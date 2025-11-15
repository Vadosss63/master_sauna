import json
from dataclasses import dataclass
from typing import Optional

from tts import speak

from voice_input import get_voice_command

from sauna_api import (
    SaunaData,
    get_current_data,
    start_session,
    stop_session,
    set_temperature,
    set_humidity,
)

from llm_controller import generate_sauna_command_string


@dataclass
class SaunaCommand:
    action: str
    target_temperature: Optional[float] = None
    target_humidity: Optional[float] = None
    message_to_user: str = ""


def apply_command_to_heater(cmd: SaunaCommand, env: SaunaData) -> SaunaData:
    """
    Вызывает функции нового API (set_temperature, set_humidity, start_session, stop_session),
    и возвращает обновлённый стейт (SaunaData).
    """
    if cmd.action == "start_session":
        print("[HEATER] Starting session.")
        start_session()

    elif cmd.action == "stop_session":
        print("[HEATER] Stopping session and turning off heater.")
        stop_session()

    elif cmd.action == "set_temperature" and cmd.target_temperature is not None:
        print(f"[HEATER] Setting temperature to {cmd.target_temperature} °C")
        set_temperature(cmd.target_temperature)

    elif cmd.action == "set_humidity" and cmd.target_humidity is not None:
        print(f"[HEATER] Setting humidity to {cmd.target_humidity} %")
        set_humidity(cmd.target_humidity)

    elif cmd.action == "report_state":
        print("[HEATER] Reporting state (no changes applied).")

    else:
        print("[HEATER] No temperature/humidity change.")

    # Получаем актуальное состояние из API
    return get_current_data()


def main():
    print("=== AI Sauna Demo (English, absolute control) ===")
    print("Try commands like:")
    print("- start the session")
    print("- make it warmer")
    print("- a bit cooler please")
    print("- set temperature to 85")
    print("- make it more humid")
    print("- what's the current temperature?")
    print("- what's the humidity?")
    print("- let's finish the session\n")

    while True:
        env = get_current_data()
        print(f"\nCurrent: {env.temperature} °C, humidity {env.humidity}%")

        # user_text = input("You: ")
        user_text = get_voice_command()
        if not user_text:
            print("Could not get voice command. Please try again.")
            continue

        print(f"You said: {user_text}")

        if user_text.strip().lower() in {"exit", "quit"}:
            print("Stopping demo.")
            return

        # 1) Получаем от AI строку с JSON
        raw_cmd = generate_sauna_command_string(user_text, env)
        # print(f"[RAW AI COMMAND] {raw_cmd}")

        # 2) Парсим её здесь, уже без знаний о LLM
        try:
            data = json.loads(raw_cmd)
        except json.JSONDecodeError as e:
            # print(f"[PARSER ERROR] Could not decode JSON from AI: {e}")
            print("Skipping this command.")
            continue

        cmd = SaunaCommand(
            action=data.get("action", "smalltalk"),
            target_temperature=data.get("target_temperature"),
            target_humidity=data.get("target_humidity"),
            message_to_user=data.get("message_to_user", ""),
        )

        env = apply_command_to_heater(cmd, env)

        answer = ""
        if cmd.action == "report_state":
            answer = f"Temperature {env.temperature} °C, humidity {env.humidity} %."
        else:
            answer = f"{cmd.message_to_user}"

        print(answer)
        speak(answer)


if __name__ == "__main__":
    main()
