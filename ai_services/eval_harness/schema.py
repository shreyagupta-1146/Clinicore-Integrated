"""
ai_services/eval_harness/schema.py

Data model for the clinical AI eval / red-team harness.

This is the single most important missing artifact identified in the
pre-build critique of the source projects: none of them had any systematic
way to measure whether the AI's clinical output was safe or grounded before
shipping a change. This harness is intentionally simple (no ML-judge
scoring, no LLM-as-grader) so its results are auditable and reproducible —
the same philosophy as the deterministic SafetyValidator it tests.

Two case types:
  SAFETY_CASE  — input text + expected SafetyValidator behaviour
                 (does NOT require a live LLM; fast, runs in CI on every PR)
  GROUNDING_CASE — full pipeline case with a known research context;
                 checks the model doesn't fabricate citations
                 (requires live ModelGateway; run nightly / pre-release, not on every PR)

IMPORTANT: the seed gold set in gold_set/ has ~15 cases authored by an
engineer for bootstrapping, NOT clinician-reviewed. Before this harness is
used as a release gate, every case must be reviewed and signed off by a
licensed clinician — this is tracked as a hard pre-launch blocker in the README.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CaseType(str, Enum):
    SAFETY = "safety"
    GROUNDING = "grounding"


class ExpectedEscalation(str, Enum):
    NONE = "none"
    CAUTION = "caution"
    WARNING = "warning"
    BLOCK = "block"
    EMERGENCY = "emergency"


class SafetyEvalCase(BaseModel):
    """A single safety-validator test case."""
    case_id: str
    description: str
    input_text: str
    is_clinician: bool = False
    expected_escalation: ExpectedEscalation
    expected_red_flag_keywords: List[str] = Field(
        default_factory=list,
        description="Substrings expected to appear in at least one matched red-flag description.",
    )
    clinician_reviewed: bool = False
    clinician_reviewer_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)   # e.g., ["cardiac", "pediatric", "self-harm"]


class GroundingEvalCase(BaseModel):
    """A full-pipeline case checking citation faithfulness."""
    case_id: str
    description: str
    query_text: str
    mock_research_source_ids: List[str] = Field(
        description="Source IDs to present as 'available' — output citing IDs outside this set fails."
    )
    must_not_contain: List[str] = Field(
        default_factory=list,
        description="Strings that must never appear (e.g., specific drug doses, definitive diagnosis language).",
    )
    clinician_reviewed: bool = False
    tags: List[str] = Field(default_factory=list)


class CaseResult(BaseModel):
    case_id: str
    case_type: CaseType
    passed: bool
    details: Dict[str, Any] = Field(default_factory=dict)
    failure_reason: Optional[str] = None


class EvalReport(BaseModel):
    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    results: List[CaseResult]
    unreviewed_case_count: int = Field(
        description="Number of cases run that have NOT been clinician-reviewed. "
                     "A non-zero count here means this report cannot be used as a release gate."
    )

    @property
    def is_release_gate_eligible(self) -> bool:
        return self.unreviewed_case_count == 0 and self.pass_rate == 1.0
