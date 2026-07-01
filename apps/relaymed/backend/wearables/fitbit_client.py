"""
apps/relaymed/backend/wearables/fitbit_client.py

Fitbit Web API client (Plane B — server-side cloud pull).

Flow:
  1. User taps "Connect Fitbit" in RelayMed → redirected to Fitbit OAuth.
  2. Fitbit redirects back with a code → exchange_code() → access + refresh tokens
     (store the refresh token encrypted in Vault, keyed by patient).
  3. A Celery job periodically calls fetch_recent() with the access token,
     merges the endpoints, and hands the raw dict to normalizer.normalize_fitbit().

Scopes needed: heartrate, oxygen_saturation, temperature, nutrition (glucose is
limited; most glucose comes from Health Connect / a CGM, not Fitbit).

NOTE: high-frequency intraday heart-rate at scale requires Fitbit's approval of
your application — basic daily summaries are self-serve.
"""

from __future__ import annotations

import base64
import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
_API_BASE = "https://api.fitbit.com/1/user/-"
_SCOPES = "heartrate oxygen_saturation temperature activity sleep"


class FitbitClient:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self._id = client_id
        self._secret = client_secret
        self._redirect = redirect_uri

    def authorize_url(self, state: str) -> str:
        return (
            f"{_AUTH_URL}?response_type=code&client_id={self._id}"
            f"&redirect_uri={self._redirect}&scope={_SCOPES.replace(' ', '%20')}&state={state}"
        )

    async def exchange_code(self, code: str) -> Dict:
        """Exchange an auth code for tokens. Store refresh_token in Vault."""
        basic = base64.b64encode(f"{self._id}:{self._secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "authorization_code", "code": code, "redirect_uri": self._redirect},
            )
            resp.raise_for_status()
            return resp.json()

    async def refresh(self, refresh_token: str) -> Dict:
        basic = base64.b64encode(f"{self._id}:{self._secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch_recent(self, access_token: str, date: str = "today") -> Dict:
        """
        Pull recent summaries and merge into the shape normalize_fitbit expects:
          { "heart_rate": [{"value","time"}], "spo2": [...], "temperature": [...] }
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        merged: Dict[str, list] = {"heart_rate": [], "spo2": [], "temperature": []}
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                hr = await client.get(f"{_API_BASE}/activities/heart/date/{date}/1d.json", headers=headers)
                if hr.status_code == 200:
                    for pt in hr.json().get("activities-heart-intraday", {}).get("dataset", []):
                        merged["heart_rate"].append({"value": pt.get("value"), "time": f"{date}T{pt.get('time','00:00:00')}"})
            except Exception as exc:
                logger.warning("fitbit_hr_fetch_failed error=%s", exc)

            try:
                spo2 = await client.get(f"{_API_BASE}/spo2/date/{date}.json", headers=headers)
                if spo2.status_code == 200:
                    avg = spo2.json().get("value", {}).get("avg")
                    if avg is not None:
                        merged["spo2"].append({"value": avg, "time": f"{date}T12:00:00"})
            except Exception as exc:
                logger.warning("fitbit_spo2_fetch_failed error=%s", exc)

        return merged
