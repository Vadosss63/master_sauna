# voice_input.py
import contextlib
import os
import sys

import speech_recognition as sr


@contextlib.contextmanager
def suppress_alsa_errors():
    """
    Временно перенаправляем stderr в /dev/null,
    чтобы скрыть варнинги ALSA/JACK при работе с микрофоном.
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    stderr_fno = sys.stderr.fileno()
    saved_stderr = os.dup(stderr_fno)
    try:
        os.dup2(devnull, stderr_fno)
        os.close(devnull)
        yield
    finally:
        os.dup2(saved_stderr, stderr_fno)
        os.close(saved_stderr)


def list_microphones() -> None:
    """
    Вспомогательная функция: вывести список доступных микрофонов.
    Можно вызвать из отдельного скрипта, чтобы понять, какой device_index использовать.
    """
    print("Available microphones:")
    for i, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"  [{i}] {name}")


def get_voice_command(
    timeout: float = 10.0,
    phrase_time_limit: float = 8.0,
    device_index: int | None = None,
) -> str:
    """
    Записывает голос с микрофона и возвращает распознанную строку (EN).

    timeout           – сколько секунд ждать начала речи
    phrase_time_limit – максимальная длина фразы
    device_index      – индекс микрофона (если None, берётся системный дефолтный)
    """

    recognizer = sr.Recognizer()

    # list_microphones()

    # Подавляем ALSA/JACK-варнинги именно на время работы с микрофоном
    with suppress_alsa_errors():
        try:
            mic = sr.Microphone(device_index=device_index)
        except OSError as e:
            print(f"⚠️  Could not access microphone: {e}")
            return ""

        print("\n🎙 Say your sauna command... (listening)")
        with mic as source:
            # Чуть подстроимся под шум
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            except sr.WaitTimeoutError:
                print("⚠️  No speech detected (timeout).")
                return ""

    try:
        text = recognizer.recognize_google(audio, language="en-US")
        print(f"🗣 Recognized: {text}")
        return text
    except sr.UnknownValueError:
        print("⚠️  Could not understand audio, please try again.")
        return ""
    except sr.RequestError as e:
        print(f"⚠️  Speech recognition service error: {e}")
        return ""
