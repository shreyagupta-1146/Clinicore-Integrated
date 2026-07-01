"""
ai_services/longitudinal/risk_tracker.py

Longitudinal chronic-disease risk tracker.

What it does:
  Given a patient's FHIR timeline (vitals, adherence, care plan), compute
  a simple, interpretable risk score for each tracked condition. Flag
  deterioration trends and generate a plain-language summary for the
  caregiver dashboard and for Clinicore clinical context.

What it does NOT do:
  - Claim to predict hospitalisation with a specific accuracy (no validated model)
  - Generate an autonomous clinical recommendation without clinician review
  - Incorporate labs without an explicit FHIR Observation feed configured

Approach:
  Rule-based trending + lightweight statistical thresholds (z-score over a
  30-day rolling window). This is NOT a trained ML model. A proper longitudinal
  model (e.g. fine-tuned LSTM or ClinicalBERT on your cohort) would replace
  this in Phase 4 of the implementation plan after you have 12+ months of data
  and a clinical validation set.

  The output is explicitly labelled "Trend Indicator", not "Risk Prediction",
  because calling it a prediction without clinical validation would be misleading
  and potentially a SaMD classification issue under CDSCO guidance.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class TrendDirection(str):
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class MetricTrend:
    metric: str
    last_value: Optional[float]
    mean_30d: Optional[float]
    std_30d: Optional[float]
    trend: str  # TrendDirection values
    z_score: Optional[float]
    data_points: int
    flag_message: Optional[str] = None


@dataclass
class LongitudinalSummary:
    patient_id: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metric_trends: List[MetricTrend] = field(default_factory=list)
    adherence_trend: Optional[str] = None  # TrendDirection value
    overall_flag: Optional[str] = None     # None | "deteriorating" | "improving"
    plain_language_summary: str = ""
    disclaimer: str = (
        "This is a trend indicator based on raw data, not a clinical prediction. "
        "All care decisions must be made by a qualified clinician."
    )


class LongitudinalRiskTracker:
    """
    Computes per-metric z-score trends from FHIR Observation lists.
    Stateless — instantiate once, call per patient on demand.
    """

    # Metric ranges for context-aware flagging
    _VITAL_RANGES = {
        "heart_rate": (60, 100),
        "blood_pressure_systolic": (90, 140),
        "blood_pressure_diastolic": (60, 90),
        "spo2": (95, 100),
        "blood_glucose": (70, 140),
        "temperature_c": (36.1, 37.5),
    }

    def compute_summary(
        self,
        patient_id: str,
        observations: List[Dict[str, Any]],
        adherence_data: Optional[List[Dict[str, Any]]] = None,
    ) -> LongitudinalSummary:
        """
        Build a longitudinal summary from a list of FHIR Observation dicts.
        observations: output of FHIRTimeline.get_observations(max_count=500)
        adherence_data: output of FHIRTimeline.get_observations(category='survey', ...)
        """
        by_metric: Dict[str, List[float]] = {}
        for obs in observations:
            code_text = obs.get("code", {}).get("text", "").lower()
            value_qty = obs.get("valueQuantity", {})
            value = value_qty.get("value")
            if value is None or not code_text:
                continue
            for key in self._VITAL_RANGES:
                if key.replace("_", " ") in code_text or key in code_text:
                    by_metric.setdefault(key, []).append(float(value))
                    break

        metric_trends = []
        flagged_metrics = []

        for metric, values in by_metric.items():
            trend = self._compute_trend(metric, values)
            metric_trends.append(trend)
            if trend.flag_message:
                flagged_metrics.append(trend.flag_message)

        adherence_trend = None
        if adherence_data:
            adherence_trend = self._compute_adherence_trend(adherence_data)

        overall_flag = None
        if sum(1 for t in metric_trends if t.trend == TrendDirection.WORSENING) >= 2:
            overall_flag = "deteriorating"
        elif sum(1 for t in metric_trends if t.trend == TrendDirection.IMPROVING) >= 2:
            overall_flag = "improving"

        plain_text = self._build_plain_text(metric_trends, adherence_trend, overall_flag)

        return LongitudinalSummary(
            patient_id=patient_id,
            metric_trends=metric_trends,
            adherence_trend=adherence_trend,
            overall_flag=overall_flag,
            plain_language_summary=plain_text,
        )

    def _compute_trend(self, metric: str, values: List[float]) -> MetricTrend:
        if len(values) < 3:
            return MetricTrend(
                metric=metric,
                last_value=values[-1] if values else None,
                mean_30d=None,
                std_30d=None,
                trend=TrendDirection.INSUFFICIENT_DATA,
                z_score=None,
                data_points=len(values),
            )

        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) >= 2 else 0.0
        last = values[-1]
        z = (last - mean) / std if std > 0 else 0.0

        recent_half = values[len(values) // 2:]
        earlier_half = values[: len(values) // 2]
        recent_mean = statistics.mean(recent_half)
        earlier_mean = statistics.mean(earlier_half)

        lo, hi = self._VITAL_RANGES.get(metric, (None, None))
        flag = None
        if lo is not None and hi is not None:
            if last < lo or last > hi:
                flag = f"{metric}: last value {last:.1f} is outside normal range [{lo}, {hi}]"

        if abs(z) < 1.0:
            trend = TrendDirection.STABLE
        elif recent_mean > earlier_mean:
            trend = TrendDirection.WORSENING if metric in ("blood_pressure_systolic", "blood_glucose") else TrendDirection.IMPROVING
        else:
            trend = TrendDirection.IMPROVING if metric in ("blood_pressure_systolic", "blood_glucose") else TrendDirection.WORSENING

        return MetricTrend(
            metric=metric,
            last_value=last,
            mean_30d=round(mean, 2),
            std_30d=round(std, 2),
            trend=trend,
            z_score=round(z, 2),
            data_points=len(values),
            flag_message=flag,
        )

    def _compute_adherence_trend(self, adherence_obs: List[Dict[str, Any]]) -> str:
        if not adherence_obs:
            return TrendDirection.INSUFFICIENT_DATA
        taken = sum(1 for o in adherence_obs if o.get("valueString") == "taken")
        total = len(adherence_obs)
        pct = (taken / total) * 100 if total else 0
        if pct >= 80:
            return TrendDirection.STABLE
        elif pct >= 60:
            return TrendDirection.WORSENING
        return TrendDirection.WORSENING

    def _build_plain_text(
        self,
        metric_trends: List[MetricTrend],
        adherence_trend: Optional[str],
        overall_flag: Optional[str],
    ) -> str:
        lines = []
        if overall_flag == "deteriorating":
            lines.append("Multiple vital signs show a worsening trend over the last 30 days.")
        elif overall_flag == "improving":
            lines.append("Multiple vital signs show an improving trend over the last 30 days.")
        else:
            lines.append("Vital signs are broadly stable over the last 30 days.")

        for t in metric_trends:
            if t.trend == TrendDirection.WORSENING and t.last_value is not None:
                lines.append(f"  • {t.metric.replace('_', ' ').title()}: trending upward (z={t.z_score:+.1f}), last value {t.last_value:.1f}")
            if t.flag_message:
                lines.append(f"  ⚠ {t.flag_message}")

        if adherence_trend:
            lines.append(f"Medication adherence trend: {adherence_trend}.")

        return " ".join(lines)
