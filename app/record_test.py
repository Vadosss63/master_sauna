import pyaudio
import wave

DURATION_SECONDS = 5
SAMPLE_RATE = 44100
CHUNK = 1024
CHANNELS = 1           # моно достаточно
FORMAT = pyaudio.paInt16
OUTPUT_FILE = "test.wav"

DEVICE_INDEX = None    # <- можно поставить число (например, 0 или 12), если знаем девайс


def list_devices(p):
    print("=== PyAudio devices ===")
    count = p.get_device_count()
    for i in range(count):
        info = p.get_device_info_by_index(i)
        print(f"[{i}] {info['name']} (max input channels: {info['maxInputChannels']})")


def main():
    p = pyaudio.PyAudio()

    # покажем устройства
    list_devices(p)

    # если не задано явно — возьмём дефолтный
    if DEVICE_INDEX is None:
        device_index = p.get_default_input_device_info()["index"]
        print(f"\nUsing default input device: {device_index}")
    else:
        device_index = DEVICE_INDEX
        print(f"\nUsing explicit device index: {device_index}")

    print(f"Recording {DURATION_SECONDS} seconds... Speak into the mic!")

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK,
    )

    frames = []

    for _ in range(0, int(SAMPLE_RATE / CHUNK * DURATION_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(OUTPUT_FILE, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    print(f"Done. Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
