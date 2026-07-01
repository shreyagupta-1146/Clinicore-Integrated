"""
apps/relaymed/backend/wearables/sources.py

Where a reading came from. Distinguishes the two ingestion planes so audit
logs and the UI can show provenance honestly.
"""

from __future__ import annotations

from enum import Enum


class WearableSource(str, Enum):
    # Plane A — on-device hubs (read by the mobile app, POSTed to /vitals/bulk)
    HEALTH_CONNECT = "health_connect"   # Android
    APPLE_HEALTH = "apple_health"       # iOS HealthKit

    # Plane B — cloud APIs pulled server-side
    FITBIT_API = "fitbit_api"           # Fitbit Web API (OAuth)
    AGGREGATOR = "aggregator"           # Terra / Spike / Rook / Validic

    # Direct / manual
    MANUAL = "manual"                   # typed by the user
    BP_MONITOR = "bp_monitor"           # e.g. Omron BLE via the mobile app

    @property
    def is_on_device(self) -> bool:
        return self in (WearableSource.HEALTH_CONNECT, WearableSource.APPLE_HEALTH)
