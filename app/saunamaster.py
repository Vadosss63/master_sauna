from sauna_module import process_sauna_interaction
from voice_input import get_voice_command

while True:
    text = get_voice_command()
    if text.strip().lower() in {"exit", "quit"}:
        break

    answer = process_sauna_interaction(text)
    print(answer)


if __name__ == "__main__":
    main()
