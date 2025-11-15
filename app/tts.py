import os
import subprocess
import tempfile
from gtts import gTTS


def speak(text: str, lang: str = "en", remove_file: bool = True):
    # создаём временный mp3 файл
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
        filename = fp.name

    # генерируем озвучку
    tts = gTTS(text=text, lang=lang)
    tts.save(filename)

    # проигрываем через ffplay (требуется установленный ffmpeg)
    subprocess.run(
        ["ffplay", "-nodisp", "-autoexit", filename],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # удаляем временный файл, если нужно
    if remove_file and os.path.exists(filename):
        os.remove(filename)
