import json
from dataclasses import dataclass
from typing import Optional

#from tts import speak

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
    Применяет команду к системе отопления сауны и возвращает обновлённый стейт.
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

    # Возврат актуального состояния
    return get_current_data()


def process_sauna_interaction(user_text: str) -> str:
    """
    Основная функция:
    - получает текущее состояние
    - вызывает LLM
    - применяет команду
    - возвращает текст ответа
    - озвучивает ответ
    """

    if not user_text:
        return "Could not get voice command. Please try again."

    env = get_current_data()

    # 1) Получаем JSON-команду от LLM
    raw_cmd = generate_sauna_command_string(user_text, env)

    try:
        data = json.loads(raw_cmd)
    except json.JSONDecodeError:
        return "Sauna Master: Sorry, I could not understand the command."

    cmd = SaunaCommand(
        action=data.get("action", "smalltalk"),
        target_temperature=data.get("target_temperature"),
        target_humidity=data.get("target_humidity"),
        message_to_user=data.get("message_to_user", ""),
    )

    # 2) Применяем
    env = apply_command_to_heater(cmd, env)

    # 3) Формируем ответ
    if cmd.action == "report_state":
        answer = f"Temperature {env.temperature} °C, humidity {env.humidity} %."
    else:
        answer = f"{cmd.message_to_user}"

    # 4) Озвучиваем
#    speak(answer)

    # 5) Возвращаем строку
    return answer
