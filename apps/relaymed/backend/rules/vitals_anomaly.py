"""
apps/relaymed/backend/rules/vitals_anomaly.py

Real, transparent statistical anomaly detection for wearable/vital readings.

Method: rolling z-score against the patient's own baseline (mean + stdev
of their last N readings for that metric), NOT a population reference
range and NOT a trained model. This is a deliberate, documented choice:

  - A trained anomaly model needs a labelled dataset of "this patient's
    abnormal reading" events that does not exist yet for either source
    project. Shipping a model trained on someone else's population data
    and presenting its output as personalised risk would repeat
    SentiHealth's worst pattern (numbers presented as real that aren't).
  - A z-score against the patient's own rolling baseline is honest about
    what it is: "this reading is unusual FOR THIS PERSON," which is also
    clinically more useful for chronic-condition monitoring than a
    population threshold (e.g., a well-controlled hypertensive patient's
    "normal" BP is not the textbook normal range).

Absolute safety floors (e.g., SpO2 < 90%) are checked FIRST and
independently of the statistical model, because some values are
dangerous regardless of personal baseline.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class VitalMetric(str, Enum):
    HEART_RATE = "heart_rate"
    SPO2 = "spo2"
    SYSTOLIC_BP = "systolic_bp"
    DIASTOLIC_BP = "diastolic_bp"
    BLOOD_GLUCOSE = "blood_glucose"
    TEMPERATURE = "temperature"


# Hard safety floors/ceilings — independent of patient baseline.
# Sources: WHO/standard clinical reference ranges for adult patients.
# These are NOT diagnostic thresholds; they exist only to catch values
# dangerous regardless of personal baseline and trigger an alert,
# never an autonomous action.
_ABSOLUTE_BOUNDS = {
    VitalMetric.SPO2: (90.0, 100.0),           # < 90% = medical emergency range
    VitalMetric.HEART_RATE: (40.0, 150.0),
    VitalMetric.SYSTOLIC_BP: (80.0, 180.0),
    VitalMetric.DIASTOLIC_BP: (50.0, 120.0),
    VitalMetric.BLOOD_GLUCOSE: (54.0, 250.0),  # mg/dL; <54 severe hypo, >250 severe hyper
    VitalMetric.TEMPERATURE: (35.0, 39.5),     # Celsius
}


class AnomalySeverity(str, Enum):
    NORMAL = "normal"
    BASELINE_DEVIATION = "baseline_deviation"   # Unusual for this patient
    ABSOLUTE_THRESHOLD = "absolute_threshold"   # Dangerous regardless of baseline


@dataclass
class AnomalyResult:
    severity: AnomalySeverity
    metric: VitalMetric
    value: float
    baseline_mean: Optional[float]
    baseline_stdev: Optional[float]
    z_score: Optional[float]
    reasoning: str


def evaluate_vital(
    metric: VitalMetric,
    value: float,
    baseline_readings: List[float],
    z_score_threshold: float = 2.5,
    min_baseline_samples: int = 7,
) -> AnomalyResult:
    # 1. Absolute safety floor — checked first, independent of baseline.
    bounds = _ABSOLUTE_BOUNDS.get(metric)
    if bounds and not (bounds[0] <= value <= bounds[1]):
        return AnomalyResult(
            severity=AnomalySeverity.ABSOLUTE_THRESHOLD,
            metric=metric,
            value=value,
            baseline_mean=None,
            baseline_stdev=None,
            z_score=None,
            reasoning=f"{metric.value}={value} is outside the safe absolute range {bounds}.",
        )

    # 2. Personal-baseline z-score — only meaningful with enough history.
    if len(baseline_readings) < min_baseline_samples:
        return AnomalyResult(
            severity=AnomalySeverity.NORMAL,
            metric=metric,
            value=value,
            baseline_mean=None,
            baseline_stdev=None,
            z_score=None,
            reasoning=(
                f"Insufficient baseline history ({len(baseline_readings)}/"
                f"{min_baseline_samples} readings) — within absolute safe range, no anomaly check performed."
            ),
        )

    mean = statistics.mean(baseline_readings)
    stdev = statistics.pstdev(baseline_readings)

    if stdev == 0:
        # Degenerate case: identical baseline readings. Any deviation is notable
        # but we avoid a division-by-zero false alarm storm.
        z = float("inf") if value != mean else 0.0
    else:
        z = (value - mean) / stdev

    if abs(z) >= z_score_threshold:
        return AnomalyResult(
            severity=AnomalySeverity.BASELINE_DEVIATION,
            metric=metric,
            value=value,
            baseline_mean=mean,
            baseline_stdev=stdev,
            z_score=z,
            reasoning=(
                f"{metric.value}={value} is {abs(z):.1f} standard deviations from this "
                f"patient's {len(baseline_readings)}-reading baseline (mean={mean:.1f})."
            ),
        )

    return AnomalyResult(
        severity=AnomalySeverity.NORMAL,
        metric=metric,
        value=value,
        baseline_mean=mean,
        baseline_stdev=stdev,
        z_score=z,
        reasoning="Within personal baseline range.",
    )
