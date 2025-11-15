from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# Basic configuration via environment, with sensible defaults
HARVIA_USERNAME = os.getenv("HARVIA_USERNAME", "harviahackathon2025@gmail.com")
HARVIA_PASSWORD = os.getenv("HARVIA_PASSWORD", "junction25!")
TARGET_DEVICE_ID = os.getenv("HARVIA_DEVICE_ID", "7772e2d7-6632-4941-94bd-ec0d403f68ae")
DEFAULT_CABIN_ID = "C1"

_client: Optional["HarviaClient"] = None


@dataclass
class SaunaData:
    """Simple value object for sauna measurement snapshot."""
    temperature: int
    humidity: int
    presence: Optional[bool] = None


def _get_client() -> "HarviaClient":
    """Lazily create and cache a HarviaClient instance."""
    global _client
    if _client is None:
        from harvia_client import HarviaClient
        c = HarviaClient(HARVIA_USERNAME, HARVIA_PASSWORD)
        c.load_config()
        c.login()
        _client = c
    return _client


# ---------------------------
# PUBLIC API (your interface)
# ---------------------------

def get_current_data() -> SaunaData:
    """
    Return latest temperature / humidity / presence
    for the configured device/cabin.
    """
    client = _get_client()
    res = client.getLatest(TARGET_DEVICE_ID, DEFAULT_CABIN_ID)

    presence_raw = res.get("presence")
    presence: Optional[bool]
    if presence_raw is None:
        presence = None
    else:
        # Often presence is 0/1 or True/False
        presence = bool(presence_raw)

    return SaunaData(
        temperature=int(res.get("temperature") or 0),
        humidity=int(res.get("humidity") or 0),
        presence=presence,
    )


def start_session() -> None:
    """Send START control to sauna session."""
    print("Start session")


def stop_session() -> None:
    """Send STOP control to sauna session."""
    print("Stop session")


def set_temperature(temperature: float) -> None:
    """Set target temperature for current device/cabin."""
    client = _get_client()
    client.setTemperature(TARGET_DEVICE_ID, temperature=temperature, cabin_id=DEFAULT_CABIN_ID)
    print(f"Set temperature to {temperature}")


def set_humidity(humidity: float) -> None:
    """Set target humidity for current device/cabin."""
    client = _get_client()
    client.setTemperature(TARGET_DEVICE_ID, humidity=humidity, cabin_id=DEFAULT_CABIN_ID)
    print(f"Set humidity to {humidity}")


def get_data_over_period(start: datetime, end: datetime) -> List[SaunaData]:
    """
    Return list of SaunaData over given time range.
    Timestamps are expected in UTC.
    """
    client = _get_client()
    hist = client.get_telemetry_history(
        TARGET_DEVICE_ID,
        start=start,
        end=end,
        cabin_id=DEFAULT_CABIN_ID,
    )

    result: List[SaunaData] = []

    if not isinstance(hist, list):
        return result

    for entry in hist:
        d = entry.get("data", {})
        t = d.get("temperature")
        h = d.get("humidity")
        if t is None or h is None:
            continue

        p_raw = d.get("presence")
        p: Optional[bool]
        if p_raw is None:
            p = None
        else:
            p = bool(p_raw)

        result.append(
            SaunaData(
                temperature=float(t),
                humidity=float(h),
                presence=p,
            )
        )

    return result
