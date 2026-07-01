"""
tests/integration/test_vitals_pipeline.py

Tests for the RelayMed vitals ingestion and anomaly detection pipeline.

These test the deterministic rules in rules/vitals_anomaly.py against
known inputs — no FHIR server or database required.
"""

from __future__ import annotations

import pytest

from apps.relaymed.backend.rules.vitals_anomaly import AnomalySeverity, VitalMetric, evaluate_vital
from apps.relaymed.backend.rules.adherence import AdherenceStatus, compute_adherence_score


# ── Vitals anomaly rules ──────────────────────────────────────────────────────

@pytest.mark.parametrize("metric,value,expected_severity", [
    # Heart rate — critical range
    (VitalMetric.HEART_RATE, 200.0, AnomalySeverity.CRITICAL),
    (VitalMetric.HEART_RATE, 25.0, AnomalySeverity.CRITICAL),
    # Heart rate — high range
    (VitalMetric.HEART_RATE, 115.0, AnomalySeverity.HIGH),
    # Heart rate — normal
    (VitalMetric.HEART_RATE, 72.0, AnomalySeverity.NONE),
    # SpO2 — critical
    (VitalMetric.SPO2, 88.0, AnomalySeverity.CRITICAL),
    # SpO2 — normal
    (VitalMetric.SPO2, 98.0, AnomalySeverity.NONE),
    # Blood glucose — critical high (DKA territory)
    (VitalMetric.BLOOD_GLUCOSE, 450.0, AnomalySeverity.CRITICAL),
    # Blood glucose — normal
    (VitalMetric.BLOOD_GLUCOSE, 100.0, AnomalySeverity.NONE),
    # Systolic BP — hypertensive crisis
    (VitalMetric.BLOOD_PRESSURE_SYSTOLIC, 185.0, AnomalySeverity.CRITICAL),
    # Systolic BP — normal
    (VitalMetric.BLOOD_PRESSURE_SYSTOLIC, 118.0, AnomalySeverity.NONE),
])
def test_vital_anomaly_classification(metric, value, expected_severity):
    result = evaluate_vital(metric=metric, value=value)
    assert result.severity == expected_severity, (
        f"metric={metric} value={value}: expected {expected_severity}, got {result.severity}"
    )


def test_anomaly_message_is_human_readable():
    result = evaluate_vital(metric=VitalMetric.HEART_RATE, value=200.0)
    assert result.severity == AnomalySeverity.CRITICAL
    assert result.message is not None
    assert len(result.message) > 10


# ── Adherence score computation ───────────────────────────────────────────────

def _make_obs(med_id: str, med_name: str, status: str) -> dict:
    return {
        "code": {"text": f"Medication adherence: {med_name}"},
        "valueString": status,
        "extension": [{"url": "medication_id", "valueString": med_id}],
    }


def test_adherence_good():
    observations = [_make_obs("med-001", "Metformin 500mg", "taken")] * 10
    results = compute_adherence_score(observations, period_days=7)
    assert len(results) == 1
    assert results[0]["adherence_pct"] == 100.0
    assert results[0]["status"] == AdherenceStatus.GOOD


def test_adherence_poor():
    observations = (
        [_make_obs("med-001", "Metformin 500mg", "taken")] * 3 +
        [_make_obs("med-001", "Metformin 500mg", "missed")] * 7
    )
    results = compute_adherence_score(observations, period_days=7)
    assert results[0]["adherence_pct"] == 30.0
    assert results[0]["status"] == AdherenceStatus.POOR


def test_adherence_multiple_medications():
    observations = (
        [_make_obs("med-001", "Metformin", "taken")] * 8 +
        [_make_obs("med-001", "Metformin", "missed")] * 2 +
        [_make_obs("med-002", "Lisinopril", "taken")] * 5 +
        [_make_obs("med-002", "Lisinopril", "missed")] * 5
    )
    results = compute_adherence_score(observations, period_days=7)
    by_id = {r["medication_id"]: r for r in results}
    assert by_id["med-001"]["status"] == AdherenceStatus.GOOD      # 80%
    assert by_id["med-002"]["status"] == AdherenceStatus.POOR      # 50%
