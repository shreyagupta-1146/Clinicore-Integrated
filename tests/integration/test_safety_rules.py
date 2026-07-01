"""
tests/integration/test_safety_rules.py

Unit-style tests for the deterministic safety validator and UEBA rules.
These do NOT require a database — they test pure rule logic.
They live in the integration suite because the CI gold-set tests are
the correct place for all safety-related test cases.

If these fail, a CI gate blocks the merge. No exceptions.
"""

from __future__ import annotations

import pytest

from ai_services.guardrails.safety_validator import EscalationLevel, SafetyValidator
from secops.ueba.analyzer import ThreatSeverity, UEBAAnalyzer
from secops.detection.rules import evaluate_all_rules


# ── Safety validator: input ───────────────────────────────────────────────────

validator = SafetyValidator()


@pytest.mark.parametrize("text,expected_level", [
    ("I can't breathe and my chest is tight", EscalationLevel.EMERGENCY),
    ("she took too many pills", EscalationLevel.EMERGENCY),
    ("I want to kill myself", EscalationLevel.EMERGENCY),
    ("patient has a rash that doesn't fade under glass", EscalationLevel.EMERGENCY),
])
def test_emergency_inputs_blocked_for_consumer(text, expected_level):
    result = validator.validate_input(text, is_clinician=False)
    assert result.escalation_level == expected_level
    assert result.allow_ai_response is False
    assert result.emergency_message is not None


@pytest.mark.parametrize("text", [
    ("I can't breathe and my chest is tight"),
    ("patient is unconscious"),
])
def test_emergency_inputs_caution_only_for_clinician(text):
    result = validator.validate_input(text, is_clinician=True)
    assert result.escalation_level == EscalationLevel.CAUTION
    assert result.allow_ai_response is True   # clinician still gets AI response


@pytest.mark.parametrize("text", [
    "patient has unintentional weight loss over 3 months",
    "coughing up blood for two days",
    "night sweats every night this week",
])
def test_red_flags_do_not_block(text):
    result = validator.validate_input(text, is_clinician=False)
    assert result.escalation_level == EscalationLevel.WARNING
    assert result.allow_ai_response is True
    assert len(result.red_flags) > 0


def test_clean_input_passes():
    result = validator.validate_input("My blood pressure was 130/85 this morning", is_clinician=False)
    assert result.escalation_level == EscalationLevel.NONE
    assert result.allow_ai_response is True


# ── Safety validator: output ──────────────────────────────────────────────────

def test_self_harm_output_blocked():
    harmful = "Here is how to harm yourself: ..."
    result = validator.validate_output(harmful)
    assert result.safe is False
    assert result.escalation_level == EscalationLevel.BLOCK
    assert "iCall" in (result.modified_content or "")


def test_diagnosis_claim_flagged():
    text = "You definitely have diabetes based on these symptoms."
    result = validator.validate_output(text)
    assert result.safe is False
    assert result.escalation_level == EscalationLevel.WARNING
    # Response is returned with disclaimer prepended, not blocked
    assert "Disclaimer" in (result.modified_content or "")


def test_clean_output_passes():
    text = "These symptoms are consistent with viral upper respiratory tract infection. Please consult your doctor."
    result = validator.validate_output(text)
    assert result.safe is True


# ── UEBA analyzer ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_brute_force_fires_after_threshold():
    analyzer = UEBAAnalyzer()
    finding = None
    for _ in range(5):
        finding = await analyzer.process_event({
            "event_type": "AUTH_FAILED",
            "actor_id": "",
            "source_ip": "192.168.1.100",
        })
    assert finding is not None
    assert finding.rule_id == "AUTH_001"
    assert finding.severity == ThreatSeverity.HIGH


@pytest.mark.asyncio
async def test_audit_chain_failure_is_critical():
    analyzer = UEBAAnalyzer()
    finding = await analyzer.process_event({
        "event_type": "AUDIT_CHAIN_WRITE_FAILURE",
        "details": "immudb unreachable",
    })
    assert finding is not None
    assert finding.severity == ThreatSeverity.CRITICAL
    assert finding.auto_escalate_after_minutes <= 5


# ── Detection rules ───────────────────────────────────────────────────────────

def test_falco_sensitive_file_read():
    event = {
        "source": "falco",
        "file": "/etc/shadow",
        "container": "clinicore-backend",
    }
    finding = evaluate_all_rules(event)
    assert finding is not None
    assert finding.rule_id == "FALCO_001"


def test_suricata_malware_sig_is_critical():
    event = {
        "source": "suricata",
        "alert_signature": "ET MALWARE CobaltStrike Beacon",
        "src_ip": "10.0.0.5",
        "dest_ip": "185.220.101.1",
    }
    finding = evaluate_all_rules(event)
    assert finding is not None
    assert finding.severity == ThreatSeverity.CRITICAL
    assert finding.auto_escalate_after_minutes <= 5


def test_clean_event_no_finding():
    event = {"source": "falco", "file": "/tmp/app.log", "event_type": "write"}
    finding = evaluate_all_rules(event)
    assert finding is None
