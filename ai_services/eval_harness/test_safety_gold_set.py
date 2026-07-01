"""
ai_services/eval_harness/test_safety_gold_set.py

Pytest wrapper around the safety gold set so it runs in the normal CI
test step (pytest) in addition to the standalone CLI runner. One test
per case so CI shows individual case failures, not one opaque red bar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_services.eval_harness.runner import load_safety_cases
from ai_services.eval_harness.scorers import score_safety_case
from ai_services.guardrails.safety_validator import SafetyValidator

_GOLD_SET_PATH = Path(__file__).parent / "gold_set" / "safety_cases.jsonl"
_CASES = load_safety_cases(_GOLD_SET_PATH)


@pytest.mark.parametrize("case", _CASES, ids=[c.case_id for c in _CASES])
def test_safety_case(case):
    validator = SafetyValidator()
    result = score_safety_case(case, validator)
    assert result.passed, result.failure_reason
