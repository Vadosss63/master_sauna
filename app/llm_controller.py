# sauna_ai.py
import json
import os
import re

from openai import OpenAI

from sauna_api import SaunaData

# В реальном проекте лучше требовать наличия ключа в env
client = OpenAI(
    base_url="https://api.featherless.ai/v1",
    api_key="rc_8824cdc6b1586fb489d0366f8fd3eb899f5266212e4519ade376d05ab71d4b72",
)


# ---------- Fallback "AI" (на случай, если LLM сломался) ----------

def _fallback_sauna_ai(user_text: str, env: SaunaData) -> dict:
    """
    Простейшая rule-based логика, чтобы демо не падало,
    если LLM или парсинг сломался.
    Возвращает dict в том же формате, что и LLM.
    """
    text = user_text.lower()

    # старт / стоп сессии
    if any(w in text for w in ("start session", "begin session", "let's start", "start sauna")):
        return {
            "action": "start_session",
            "target_temperature": None,
            "target_humidity": None,
            "message_to_user": "Starting your sauna session. Enjoy the heat!",
        }

    if any(w in text for w in ("finish", "stop", "end session", "shutdown", "turn off")):
        return {
            "action": "stop_session",
            "target_temperature": None,
            "target_humidity": None,
            "message_to_user": "Okay, I will stop the session and turn off the heater.",
        }

    # спросить состояние
    if any(w in text for w in ("temperature", "hot", "warm", "humidity", "steam", "status", "state")):
        return {
            "action": "report_state",
            "target_temperature": None,
            "target_humidity": None,
            "message_to_user": f"The current temperature is {env.temperature:.1f} °C and humidity is {env.humidity:.1f} %.",
        }

    # сделать теплее / прохладнее
    if any(w in text for w in ("hotter", "warmer", "heat up")):
        new_temp = min(env.temperature + 5.0, 110.0)
        return {
            "action": "set_temperature",
            "target_temperature": new_temp,
            "target_humidity": None,
            "message_to_user": f"I will make it warmer and set the temperature to {new_temp:.1f} °C.",
        }

    if any(w in text for w in ("cooler", "colder", "cool down")):
        new_temp = max(env.temperature - 5.0, 0.0)
        return {
            "action": "set_temperature",
            "target_temperature": new_temp,
            "target_humidity": None,
            "message_to_user": f"I will make it cooler and set the temperature to {new_temp:.1f} °C.",
        }

    # сделать влажнее / суше
    if any(w in text for w in ("more humid", "more steam", "wetter")):
        new_hum = min(env.humidity + 2.0, 100.0)
        return {
            "action": "set_humidity",
            "target_temperature": None,
            "target_humidity": new_hum,
            "message_to_user": f"I will increase humidity to {new_hum:.1f} %.",
        }

    if any(w in text for w in ("less humid", "less steam", "drier")):
        new_hum = max(env.humidity - 2.0, 0.0)
        return {
            "action": "set_humidity",
            "target_temperature": None,
            "target_humidity": new_hum,
            "message_to_user": f"I will decrease humidity to {new_hum:.1f} %.",
        }

    # число в тексте → считаем температурой
    m = re.search(r"(\d{2,3})", text)
    if m:
        t = float(m.group(1))
        if t > 110:
            return {
                "action": "smalltalk",
                "target_temperature": None,
                "target_humidity": None,
                "message_to_user": "That temperature is too high for safety. Let's stay below 110 °C.",
            }
        return {
            "action": "set_temperature",
            "target_temperature": t,
            "target_humidity": None,
            "message_to_user": f"Setting the temperature to {t:.1f} °C.",
        }

    # просто болтовня
    return {
        "action": "smalltalk",
        "target_temperature": None,
        "target_humidity": None,
        "message_to_user": "Let's just relax and enjoy the heat.",
    }


# ---------- Утилиты для очистки и парсинга ответа LLM ----------

def _clean_llm_output(raw: str) -> str:
    """
    Убираем <think>...</think>, обёртки ```json ... ``` и лишний мусор.
    Оставляем максимально "похожее на JSON".
    """
    txt = raw.strip()

    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.DOTALL | re.IGNORECASE).strip()

    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z0-9]*\s*", "", txt)
        txt = re.sub(r"```$", "", txt.strip())

    return txt.strip()


def _parse_command_dict_from_raw(raw: str, user_text: str, env: SaunaData) -> dict:
    cleaned = _clean_llm_output(raw)

    def _normalize(data: dict) -> dict:
        return {
            "action": data.get("action", "smalltalk"),
            "target_temperature": data.get("target_temperature"),
            "target_humidity": data.get("target_humidity"),
            "message_to_user": data.get("message_to_user", ""),
        }

    # 1) Прямая попытка json.loads
    try:
        data = json.loads(cleaned)
        return _normalize(data)
    except json.JSONDecodeError:
        pass

    # 2) Попробовать вытащить первый { ... } блок
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        candidate = m.group(0)
        try:
            data = json.loads(candidate)
            return _normalize(data)
        except json.JSONDecodeError:
            pass

    #print("[AI WARNING] Could not parse JSON from model output. Raw response:")
    #print(raw)
    return _fallback_sauna_ai(user_text, env)


def generate_sauna_command_string(user_text: str, env: SaunaData) -> str:
    """
    Interface to communicate with LLM

    {
      "action": "set_temperature" | "set_humidity" | "start_session" | "stop_session" | "report_state" | "smalltalk",
      "target_temperature": number or null,
      "target_humidity": number or null,
      "message_to_user": "..."
    }
    """
    system_prompt = """
You are a virtual sauna master — a friendly assistant that controls a sauna heater
and keeps a pleasant atmosphere for the user.

Your job:
- Understand the user's request in natural language.
- Use the CURRENT environment state (temperature, humidity).
- Decide what to do.
- Return a SINGLE JSON object describing the action.

MANDATORY JSON FORMAT (NO EXTRA FIELDS, NO COMMENTS):
{
  "action": "start_session" |
            "stop_session" |
            "set_temperature" |
            "set_humidity" |
            "report_state" |
            "smalltalk",
  "target_temperature": number or null,
  "target_humidity": number or null,
  "message_to_user": "short friendly English message"
}

CRITICAL JSON RULES (STRICT):
- Output MUST be VALID JSON:
  - use double quotes "..."
  - no trailing commas
  - no comments
  - no NaN, Infinity, or undefined
- Keys MUST be exactly:
  "action", "target_temperature", "target_humidity", "message_to_user"
  in any order, but no other keys.
- "action" MUST be one of:
  "start_session", "stop_session", "set_temperature",
  "set_humidity", "report_state", "smalltalk".
- "target_temperature" and "target_humidity":
  - MUST be either a number (e.g. 80 or 80.0) or null.
  - MUST NOT be strings (no "80").
- If the action does not logically use a target (e.g. "start_session",
  "stop_session", "report_state", "smalltalk") then set:
  "target_temperature": null
  "target_humidity": null
- If you are unsure what to do, ALWAYS choose:
  "action": "smalltalk",
  "target_temperature": null,
  "target_humidity": null

BEHAVIOR RULES:

- The user can:
  - ask to start the session (e.g. "start the sauna", "begin session")
      → use "start_session".
  - ask to stop the session (e.g. "stop", "finish", "end the session")
      → use "stop_session".
  - ask to make it warmer/cooler:
      * If the user does NOT specify an exact temperature:
          - you MUST compute a NEW ABSOLUTE temperature based on the current state.
          - use "set_temperature" with target_temperature.
          - by default use a step of about +5°C for "warmer" and -5°C for "cooler",
            unless the user clearly asks for a different change ("much hotter", etc.).
  - ask to make it more / less humid:
      * If the user does NOT specify an exact humidity:
          - you MUST compute a NEW ABSOLUTE humidity.
          - by default use a step of about +2% for "more humid" and -2% for "less humid".
          - use "set_humidity" with target_humidity.
  - ask for the current temperature/humidity/state:
      * use "report_state".
      * set both targets to null.
  - just chat or talk:
      * use "smalltalk".
      * set both targets to null.

SAFETY:

- Never set temperature above 110°C.
- Never set humidity below 0% or above 100%.
- If the user asks for unsafe values, you MUST stay safe:
  - Either clip to the safe range,
    OR choose "smalltalk" and explain that the request is unsafe.
- If you clip, you MUST write the clipped value into target_temperature/target_humidity
  and mention that you adjusted it for safety.

ALWAYS:

- Respond with a SINGLE JSON object.
- No markdown.
- No text outside JSON.
"""

    user_prompt = f"""
Current environment:
- temperature: {env.temperature} °C
- humidity: {env.humidity} %

User said:
\"\"\"{user_text}\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3-0324",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        raw = response.choices[0].message.content
        if isinstance(raw, list):
            raw = "".join(part["text"] for part in raw)

        cmd_dict = _parse_command_dict_from_raw(raw, user_text, env)

    except Exception as e:
        #print(f"[AI WARNING] LLM call failed ({type(e).__name__}): {e}")
        #print("[AI WARNING] Falling back to simple rule-based logic.")
        cmd_dict = _fallback_sauna_ai(user_text, env)

    return json.dumps(cmd_dict)
