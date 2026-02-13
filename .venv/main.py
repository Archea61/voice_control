import pyaudio
import threading
import time
from speechkit import Session, DataStreamingRecognition
from pynput.keyboard import Controller, Key

# Здесь вместо API_KEY мы используем OAuth-токен + catalog_id
OAUTH_TOKEN = ""
CATALOG_ID = ""

TRIGGER_WORDS = ["триггерные слова"]
TRIGGER_COOLDOWN = (2.0)

# Максимальное время жизни одного стрима (чуть меньше 5 минут)
MAX_STREAM_TIME = 290  # 4 мин 50 сек

# Создаём сессию через OAuth
session = Session.from_yandex_passport_oauth_token(OAUTH_TOKEN, CATALOG_ID)

keyboard = Controller()

# Захват аудио с микрофона
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4096)

def audio_generator():
    while True:
        data = stream.read(4096, exception_on_overflow=False)
        yield data

def run_recognizer():
    """Один запуск распознавания (перезапускается каждые ~5 мин)."""
    stream_recognizer = DataStreamingRecognition(
        session=session,
        language_code="ru-RU",
        profanity_filter=False,
        partial_results=True,
        single_utterance=False,
        audio_encoding="LINEAR16_PCM",
        sample_rate_hertz=16000,
    )

    last_trigger_time = 0
    start_time = time.time()

    for texts, is_final, _ in stream_recognizer.recognize(audio_generator):
        # Проверяем, не пора ли перезапускать стрим
        if time.time() - start_time > MAX_STREAM_TIME:
            print("⚡ Время жизни стрима истекло — перезапуск...")
            break

        if not texts or is_final:
            continue

        text = texts[0].lower()
        print("Промежуточно распознано:", text)

        # Проверяем триггерные слова
        for word in TRIGGER_WORDS:
            if word in text:
                now = time.time()
                if now - last_trigger_time >= TRIGGER_COOLDOWN:
                    print(f"Триггер '{word}' найден — нажимаем '+' и Enter")
                    with keyboard.pressed(Key.shift):
                        keyboard.press('=')
                        keyboard.release('=')
                    keyboard.press(Key.enter)
                    keyboard.release(Key.enter)
                    last_trigger_time = now
                break

def process_recognition():
    while True:
        try:
            run_recognizer()
        except Exception as e:
            print("Ошибка распознавания:", e)
            time.sleep(2)

if __name__ == "__main__":
    thread = threading.Thread(target=process_recognition, daemon=True)
    thread.start()
    print("Слушаю микрофон... (авто-перезапуск каждые ~4 мин 50 сек)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Остановка")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()