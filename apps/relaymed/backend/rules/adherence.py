"""
apps/relaymed/backend/rules/adherence.py

Deterministic medication-adherence rule evaluation.

Design note: this is intentionally a plain rule, not a model. The original
SentiHealth project's pattern of presenting fabricated ML metrics as if they
were measured is exactly what this integration explicitly removes (see
README "What was removed"). A missed-dose alert is a fact (the dose log
says "missed"), not a prediction — there is nothing here that benefits from
being probabilistic, and a wrong "AI-detected non-adherence" alert sent to
a worried adult child about their elderly parent is a trust-destroying
false positive. Keep it simple and explainable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List

from apps.relaymed.backend.models.medication import DoseLogORM


class AdherenceAlertLevel(str, Enum):
    NONE = "none"
    SINGLE_MISS = "single_miss"          # Informational; no caregiver alert
    CONSECUTIVE_MISS = "consecutive_miss"  # Caregiver alert threshold
    PATTERN_MISS = "pattern_miss"          # 3+ misses in last 7 days — escalate


@dataclass
class AdherenceEvaluation:
    level: AdherenceAlertLevel
    consecutive_missed: int
    missed_in_last_7_days: int
    reasoning: str


def evaluate_adherence(
    recent_logs: List[DoseLogORM],
    consecutive_miss_threshold: int = 2,
    pattern_window_days: int = 7,
    pattern_miss_threshold: int = 3,
    now: datetime | None = None,
) -> AdherenceEvaluation:
    """
    recent_logs MUST be sorted oldest -> newest and cover at least
    `pattern_window_days` of scheduled doses for the pattern check to be meaningful.
    """
    if not recent_logs:
        return AdherenceEvaluation(
            level=AdherenceAlertLevel.NONE,
            consecutive_missed=0,
            missed_in_last_7_days=0,
            reasoning="No dose logs available.",
        )

    consecutive_missed = 0
    for log in reversed(recent_logs):
        if log.status == "missed":
            consecutive_missed += 1
        elif log.status == "taken":
            break
        # status == "pending" (not yet due) is skipped, doesn't break the streak

    now = now or datetime.now(recent_logs[-1].scheduled_for.tzinfo)
    cutoff = now.timestamp() - (pattern_window_days * 86400)
    missed_in_window = sum(
        1 for log in recent_logs
        if log.status == "missed" and log.scheduled_for.timestamp() >= cutoff
    )

    if missed_in_window >= pattern_miss_threshold:
        level = AdherenceAlertLevel.PATTERN_MISS
        reasoning = (
            f"{missed_in_window} missed doses in the last {pattern_window_days} days "
            f"(threshold: {pattern_miss_threshold})."
        )
    elif consecutive_missed >= consecutive_miss_threshold:
        level = AdherenceAlertLevel.CONSECUTIVE_MISS
        reasoning = f"{consecutive_missed} consecutive missed doses (threshold: {consecutive_miss_threshold})."
    elif consecutive_missed == 1:
        level = AdherenceAlertLevel.SINGLE_MISS
        reasoning = "Single missed dose — informational only, no caregiver alert."
    else:
        level = AdherenceAlertLevel.NONE
        reasoning = "Adherence within expected range."

    return AdherenceEvaluation(
        level=level,
        consecutive_missed=consecutive_missed,
        missed_in_last_7_days=missed_in_window,
        reasoning=reasoning,
    )


# ── FHIR-observation-based summary (used by API routes) ───────────────────────

class AdherenceStatus:
    GOOD = "good"           # >= 80%
    MODERATE = "moderate"   # 60-79%
    POOR = "poor"           # < 60%


def compute_adherence_score(
    observations: list,
    period_days: int = 7,
) -> list:
    """
    Compute per-medication adherence from FHIR Observation dicts.
    (observations already filtered to code.text starting with 'Medication adherence:')
    """
    from collections import defaultdict
    by_med: dict = defaultdict(lambda: {"scheduled": 0, "taken": 0, "name": ""})

    for obs in observations:
        extensions = obs.get("extension", [])
        med_id = next((e.get("valueString") for e in extensions if e.get("url") == "medication_id"), None)
        if not med_id:
            continue
        med_name = obs.get("code", {}).get("text", "").replace("Medication adherence: ", "")
        status = obs.get("valueString", "unknown")
        by_med[med_id]["name"] = med_name
        by_med[med_id]["scheduled"] += 1
        if status == "taken":
            by_med[med_id]["taken"] += 1

    results = []
    for med_id, data in by_med.items():
        scheduled = data["scheduled"]
        taken = data["taken"]
        pct = (taken / scheduled * 100) if scheduled > 0 else 0.0
        status = AdherenceStatus.GOOD if pct >= 80 else (AdherenceStatus.MODERATE if pct >= 60 else AdherenceStatus.POOR)
        results.append({
            "medication_id": med_id,
            "medication_name": data["name"],
            "period_days": period_days,
            "doses_scheduled": scheduled,
            "doses_taken": taken,
            "adherence_pct": round(pct, 1),
            "status": status,
        })
    return results
