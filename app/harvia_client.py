#!/usr/bin/env python3
import os
import sys
import json
import logging
from typing import Any, Dict, Optional, List, Union
from datetime import datetime

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
log = logging.getLogger("harvia-api")

ENDPOINTS_URL = "https://prod.api.harvia.io/endpoints"


def pretty(title: str, data: Any) -> None:
    """Pretty-print helper for debugging."""
    print(f"\n=== {title} ===")
    try:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        print(data)


def attrs_to_dict(device: Dict[str, Any]) -> Dict[str, Any]:
    """Convert 'attr' list from device payload into a plain dict."""
    result: Dict[str, Any] = {}
    for item in device.get("attr", []):
        k = item.get("key")
        v = item.get("value")
        if k is not None:
            result[k] = v
    return result


class HarviaClient:
    """Thin client over Harvia REST API."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.session = requests.Session()

        self.rest_generics: str = ""
        self.rest_device: str = ""
        self.rest_data: str = ""
        self.graphql: Dict[str, Any] = {}

        self.id_token: Optional[str] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    # ---------- bootstrap ----------

    def load_config(self) -> None:
        """Fetch base URLs for REST / GraphQL endpoints."""
        log.info("Fetching API configuration...")
        resp = self.session.get(ENDPOINTS_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        endpoints = data["endpoints"]
        rest = endpoints["RestApi"]

        self.rest_generics = rest["generics"]["https"].rstrip("/")
        self.rest_device = rest.get("device", rest["generics"])["https"].rstrip("/")
        self.rest_data = rest.get("data", rest["generics"])["https"].rstrip("/")
        self.graphql = endpoints.get("GraphQL", {})

    def _auth_headers(self) -> Dict[str, str]:
        """Build auth headers with ID token if present."""
        headers = {"Content-Type": "application/json"}
        if self.id_token:
            headers["Authorization"] = f"Bearer {self.id_token}"
        return headers

    # ---------- auth ----------

    def login(self) -> None:
        """Authenticate user and cache tokens."""
        if not self.rest_generics:
            self.load_config()

        url = f"{self.rest_generics}/auth/token"
        payload = {"username": self.username, "password": self.password}

        resp = self.session.post(url, json=payload, timeout=10)
        resp.raise_for_status()

        tokens = resp.json()
        self.id_token = tokens["idToken"]
        self.access_token = tokens.get("accessToken")
        self.refresh_token = tokens.get("refreshToken")

    # ---------- low-level HTTP ----------

    def _get(self, base: str, path: str, params=None) -> Any:
        """Internal GET helper."""
        url = f"{base}{path}"
        resp = self.session.get(url, headers=self._auth_headers(), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, base: str, path: str, body: Dict[str, Any]) -> Any:
        """Internal POST helper."""
        url = f"{base}{path}"
        resp = self.session.post(url, headers=self._auth_headers(), json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, base: str, path: str, body: Dict[str, Any]) -> Any:
        """Internal PATCH helper."""
        url = f"{base}{path}"
        resp = self.session.patch(url, headers=self._auth_headers(), json=body, timeout=10)
        #resp.raise_for_status()
        return resp.json()

    # ---------- device REST ----------

    def get_devices_raw(self) -> Dict[str, Any]:
        """Return raw device list for current account."""
        if not self.id_token:
            self.login()
        return self._get(self.rest_device, "/devices")

    def get_device_state(self, device_id: str, cabin_id: Optional[str] = None) -> Any:
        """Return current logical state of a device/cabin."""
        if not self.id_token:
            self.login()
        params = {"deviceId": device_id}
        if cabin_id:
            params["subId"] = cabin_id
        return self._get(self.rest_device, "/devices/state", params)

    def get_device_latest_raw(self, device_id: str) -> Any:
        """Raw 'latest' payload for a device (if this endpoint is available)."""
        if not self.id_token:
            self.login()
        return self._get(self.rest_device, f"/devices/{device_id}/latest")

    def setTemperature(
        self,
        device_id: str,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        cabin_id: str = "C1",
    ) -> Any:
        """
        Set target temperature / humidity for given device/cabin.
        Any of temperature / humidity can be omitted.
        """
        if not self.id_token:
            self.login()

        body: Dict[str, Any] = {"deviceId": device_id}
        if temperature is not None:
            body["temperature"] = temperature
        if humidity is not None:
            body["humidity"] = humidity
        if cabin_id:
            body["cabin"] = {"id": cabin_id}

        return self._patch(self.rest_device, "/devices/target", body)

    def control_session(
        self,
        device_id: str,
        action: str,
        cabin_id: str = "C1",
    ) -> Any:
        """
        Control sauna session (e.g. START / STOP) for given device/cabin.

        NOTE: Path and payload may need adjustment according to Harvia docs.
        """
        if not self.id_token:
            self.login()

        body: Dict[str, Any] = {
            "deviceId": device_id,
            "action": action,
        }
        if cabin_id:
            body["cabin"] = {"id": cabin_id}

        # If the actual backend uses different path, tweak here.
        return self._post(self.rest_device, "/devices/session", body)

    # ---------- telemetry history ----------

    def get_telemetry_history(
        self,
        device_id: str,
        start: Union[str, datetime],
        end: Union[str, datetime],
        cabin_id: str = "C1",
    ) -> Any:
        """Return telemetry history between start/end for a device/cabin."""
        if not self.id_token:
            self.login()

        if isinstance(start, datetime):
            start = start.isoformat()

        if isinstance(end, datetime):
            end = end.isoformat()

        params = {
            "deviceId": device_id,
            "startTimestamp": start,
            "endTimestamp": end,
            "cabinId": cabin_id,
        }

        return self._get(self.rest_data, "/data/telemetry-history", params)

    # ---------- high-level helpers ----------

    def getLatest(self, device_id: str, cabin_id: str = "C1") -> Dict[str, Any]:
        """
        High-level latest data helper.

        Returns:
            {
              "temperature": ...,
              "humidity": ...,
              "presence": ...,
              "raw": <original-latest-payload>
            }
        """
        try:
            latest = self.get_device_latest_raw(device_id)
        except Exception:
            latest = self.get_latest_data_raw(device_id, cabin_id)

        data = latest.get("data", {})
        return {
            "temperature": data.get("temp"),
            "humidity": data.get("hum"),
            "presence": data.get("presence"),
            "raw": latest,
        }

    def get_latest_data_raw(self, device_id: str, cabin_id: str = "C1") -> Any:
        """Raw latest measurement payload from /data/latest-data."""
        if not self.id_token:
            self.login()
        params = {"deviceId": device_id, "cabinId": cabin_id}
        return self._get(self.rest_data, "/data/latest-data", params)

    # Convenience 'getTemperature' wrapper

    def getTemperature(self, device_id: str, cabin_id: str = "C1") -> Optional[float]:
        """Return only the latest temperature for given device/cabin."""
        latest = self.getLatest(device_id, cabin_id)
        t = latest.get("temperature")
        return float(t) if t is not None else None
