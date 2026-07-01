"""
apps/relaymed/backend/wearables/normalizer.py

The single place that turns any wearable payload into a canonical list of
readings the rest of RelayMed understands (VitalMetric + value + timestamp +
source). Everything downstream — the anomaly z-score, the FHIR Observation,
the caregiver alert — operates on NormalizedReading, so adding a new device
means adding ONE mapping here, not touching the pipeline.

Supported payload shapes:
  - Android Health Connect records   (mobile app → /vitals/bulk)
  - iOS Apple HealthKit samples       (mobile app → /vitals/bulk)
  - Fitbit Web API JSON               (server pull)
  - Aggregator normalized payload     (Terra-style webhook)

Unit note: Health Connect/HealthKit temperature is Celsius; the app's UI uses
°F elsewhere, but we store the SI value and let the read layer format. Glucose
is mg/dL throughout (India clinical convention).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apps.relaymed.backend.rules.vitals_anomaly import VitalMetric
from apps.relaymed.backend.wearables.sources import WearableSource

logger = logging.getLogger(__name__)


@dataclass
class NormalizedReading:
    metric: VitalMetric
    value: float
    unit: str
    recorded_at: datetime
    source: WearableSource
    device_display: str = ""


# ── Health Connect record type → our metric ──────────────────────────────────
# Health Connect uses record class names; the mobile SDK sends record["type"].
_HEALTH_CONNECT_MAP = {
    "HeartRate": (VitalMetric.HEART_RATE, "bpm"),
    "OxygenSaturation": (VitalMetric.SPO2, "%"),
    "BloodPressureSystolic": (VitalMetric.SYSTOLIC_BP, "mmHg"),
    "BloodPressureDiastolic": (VitalMetric.DIASTOLIC_BP, "mmHg"),
    "BloodGlucose": (VitalMetric.BLOOD_GLUCOSE, "mg/dL"),
    "BodyTemperature": (VitalMetric.TEMPERATURE, "Cel"),
}

# ── Apple HealthKit sample identifier → our metric ───────────────────────────
_HEALTHKIT_MAP = {
    "HKQuantityTypeIdentifierHeartRate": (VitalMetric.HEART_RATE, "bpm"),
    "HKQuantityTypeIdentifierOxygenSaturation": (VitalMetric.SPO2, "%"),
    "HKQuantityTypeIdentifierBloodPressureSystolic": (VitalMetric.SYSTOLIC_BP, "mmHg"),
    "HKQuantityTypeIdentifierBloodPressureDiastolic": (VitalMetric.DIASTOLIC_BP, "mmHg"),
    "HKQuantityTypeIdentifierBloodGlucose": (VitalMetric.BLOOD_GLUCOSE, "mg/dL"),
    "HKQuantityTypeIdentifierBodyTemperature": (VitalMetric.TEMPERATURE, "Cel"),
}

# ── Aggregator (Terra-style) canonical field → our metric ────────────────────
_AGGREGATOR_MAP = {
    "heart_rate_bpm": (VitalMetric.HEART_RATE, "bpm"),
    "oxygen_saturation": (VitalMetric.SPO2, "%"),
    "systolic_bp_mmhg": (VitalMetric.SYSTOLIC_BP, "mmHg"),
    "diastolic_bp_mmhg": (VitalMetric.DIASTOLIC_BP, "mmHg"),
    "blood_glucose_mg_dl": (VitalMetric.BLOOD_GLUCOSE, "mg/dL"),
    "temperature_celsius": (VitalMetric.TEMPERATURE, "Cel"),
}


def _parse_ts(raw: Optional[str]) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def normalize_health_connect(records: List[Dict[str, Any]], device: str = "Health Connect") -> List[NormalizedReading]:
    """records: list of {type, value, unit?, time} sent by the Android app."""
    return _normalize_generic(records, _HEALTH_CONNECT_MAP, WearableSource.HEALTH_CONNECT, device, key="type")


def normalize_healthkit(samples: List[Dict[str, Any]], device: str = "Apple Health") -> List[NormalizedReading]:
    """samples: list of {identifier, value, time} sent by the iOS app."""
    return _normalize_generic(samples, _HEALTHKIT_MAP, WearableSource.APPLE_HEALTH, device, key="identifier")


def normalize_aggregator(payload: Dict[str, Any]) -> List[NormalizedReading]:
    """
    Terra-style webhook body:
      { "user": {...}, "data": [ { "metadata": {...}, "vitals": {field: value, timestamp} } ] }
    We accept a flattened list of samples under payload["samples"] too.
    """
    out: List[NormalizedReading] = []
    device = payload.get("user", {}).get("provider", "aggregator")
    samples = payload.get("samples")
    if samples is None:
        # flatten Terra-style nested structure
        samples = []
        for block in payload.get("data", []):
            vitals = block.get("vitals", {})
            ts = vitals.get("timestamp")
            for field, val in vitals.items():
                if field == "timestamp":
                    continue
                samples.append({"field": field, "value": val, "time": ts})
    for s in samples:
        mapping = _AGGREGATOR_MAP.get(s.get("field", ""))
        val = _safe_float(s.get("value"))
        if mapping and val is not None:
            metric, unit = mapping
            out.append(NormalizedReading(metric, val, unit, _parse_ts(s.get("time")), WearableSource.AGGREGATOR, device))
    return out


def normalize_fitbit(fitbit_json: Dict[str, Any], device: str = "Fitbit") -> List[NormalizedReading]:
    """
    Minimal mapping for Fitbit Web API summary responses. Fitbit splits metrics
    across endpoints (activities/heart, spo2, etc.); we accept a merged dict:
      { "heart_rate": [{"value": 72, "time": "..."}], "spo2": [...], ... }
    """
    field_map = {
        "heart_rate": (VitalMetric.HEART_RATE, "bpm"),
        "spo2": (VitalMetric.SPO2, "%"),
        "glucose": (VitalMetric.BLOOD_GLUCOSE, "mg/dL"),
        "temperature": (VitalMetric.TEMPERATURE, "Cel"),
    }
    out: List[NormalizedReading] = []
    for field, series in fitbit_json.items():
        mapping = field_map.get(field)
        if not mapping or not isinstance(series, list):
            continue
        metric, unit = mapping
        for point in series:
            val = _safe_float(point.get("value"))
            if val is not None:
                out.append(NormalizedReading(metric, val, unit, _parse_ts(point.get("time")), WearableSource.FITBIT_API, device))
    return out


def _normalize_generic(records, mapping, source, device, key) -> List[NormalizedReading]:
    out: List[NormalizedReading] = []
    for r in records:
        m = mapping.get(r.get(key, ""))
        val = _safe_float(r.get("value"))
        if m and val is not None:
            metric, unit = m
            out.append(NormalizedReading(metric, val, r.get("unit") or unit, _parse_ts(r.get("time")), source, r.get("device") or device))
        else:
            logger.debug("wearable_unmapped %s=%s", key, r.get(key))
    return out
