import pyaudio
import threading
import time
from speechkit import Session, DataStreamingRecognition
from pynput.keyboard import Controller, Key

# Здесь вместо API_KEY мы используем OAuth-токен + catalog_id
OAUTH_TOKEN = ""
CATALOG_ID = ""

START_WORD = "запись"
STOP_WORD = "стоп"
ENTER_WORD = "янтарь"
DELETE_WORD = "баста"
COMMA_WORD = "факс"
DOT_WORD = "топка"

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

def handle_command(word: str) -> bool:
    """
    Выполняет действие для командного слова.
    Возвращает True, если слово было командой (и не должно печататься).
    """
    if word == ENTER_WORD:
        print("⏎ Нажат Enter")
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)
        return True

    if word == DELETE_WORD:
        print("⌫ Удаляю слово (5 раз Ctrl+Backspace)")
        for _ in range(5):
            with keyboard.pressed(Key.ctrl):
                keyboard.press(Key.backspace)
                keyboard.release(Key.backspace)
        return True

    if word == COMMA_WORD:
        print("➕ Ставлю запятую")
        keyboard.press(Key.backspace)
        keyboard.release(Key.backspace)
        keyboard.type(", ")
        return True

    if word == DOT_WORD:
        print("ставлю точку")
        keyboard.press(Key.backspace)
        keyboard.release(Key.backspace)
        keyboard.type(". ")
        return True

    return False

def run_recognizer():
    """Один запуск распознавания (перезапускается каждые ~5 мин)."""
    stream_recognizer = DataStreamingRecognition(
        session=session,
        language_code="ru-RU",
        profanity_filter=False,
        partial_results=False,  # только финальные результаты
        single_utterance=False,
        audio_encoding="LINEAR16_PCM",
        sample_rate_hertz=16000,
    )

    start_time = time.time()
    dictation_mode = False

    for texts, is_final, _ in stream_recognizer.recognize(audio_generator):
        # Проверяем, не пора ли перезапускать стрим
        if time.time() - start_time > MAX_STREAM_TIME:
            print("⚡ Время жизни стрима истекло — перезапуск...")
            break

        if not texts:
            continue

        text = texts[0].lower()
        print("Распознано:", text)

        words = text.split()

        for word in words:
            # Управление режимом диктовки
            if word == START_WORD:
                dictation_mode = True
                print("🎤 Диктовка включена")
                continue

            if not dictation_mode:
                # пока режим диктовки не включён — игнорим
                continue

            if word == STOP_WORD:
                dictation_mode = False
                print("🛑 Диктовка выключена")
                continue

            # Проверяем, не является ли слово командой
            if handle_command(word):
                continue

            # Если обычное слово — печатаем
            print("⌨️ Печатаю:", word)
            keyboard.type(word + " ")

def process_recognition():
    """Бесконечный цикл с авто-перезапуском."""
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