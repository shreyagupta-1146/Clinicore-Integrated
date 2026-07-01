"""
secops/feedback/retraining_loop.py

Self-improving detection feedback loop — ported and generalised from
SentiHealth's deception/feedback.py + review_queue.py.

Two ideas worth keeping from SentiHealth:

1. DECEPTION-AS-ORACLE labelling: any session that touched honey-data / a decoy
   canary is an attack by definition, so it yields a *ground-truth* label with
   zero human ambiguity. Those labels flow straight into the retraining queue
   marked human_confirmed=True (source="mirage_oracle").

2. POISONING QUARANTINE: before any human-approved labels are accepted for
   retraining, check whether accepting them would shift the tier/label
   distribution suspiciously (an insider "normalising" real attacks to blind
   the model). Suspicious batches are quarantined and require explicit override.
   Mirage-oracle labels are trusted and skip the quarantine.

This is what makes detection get MORE accurate over time instead of stale —
and it defends the learning loop itself against manipulation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# A batch that shifts the High-tier fraction by more than this vs. baseline is
# flagged as a potential poisoning attempt.
POISON_DRIFT_THRESHOLD = 0.25


class LabelSource(str, Enum):
    MIRAGE_ORACLE = "mirage_oracle"   # decoy interaction — ground truth
    ANALYST = "analyst"               # human-labelled, subject to quarantine
    USER_FEEDBACK = "user_feedback"   # thumbs up/down from the AI feedback queue


@dataclass
class RetrainingCandidate:
    incident_id: str
    tier: str                         # Low | Medium | High
    explanation: str
    source: LabelSource
    top_features: List[str] = field(default_factory=list)   # SHAP-style attribution
    human_confirmed: bool = False
    canary_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    quarantined: bool = False
    quarantine_reason: str = ""


class RetrainingQueue:
    """
    In-memory retraining queue (persist to Postgres `secops_events` / a dedicated
    table in production). Handles mirage auto-confirmation and poisoning defence.
    """

    def __init__(self):
        self._candidates: Dict[str, RetrainingCandidate] = {}

    # ── ingest ────────────────────────────────────────────────────────────────
    def record_flagged_session(
        self, session_id: str, tier: str, score: float, touched_decoy: bool,
        canary_id: str = "", top_features: Optional[List[str]] = None,
    ) -> RetrainingCandidate:
        """
        Called by the sentinel when a session verdict is issued. If the session
        touched decoy/honey-data, it's a confirmed attack (oracle label).
        """
        source = LabelSource.MIRAGE_ORACLE if touched_decoy else LabelSource.ANALYST
        cand = RetrainingCandidate(
            incident_id=f"sess_{session_id[:12]}",
            tier=tier,
            explanation=(
                f"Decoy-confirmed attack (canary {canary_id}), score {score:.3f}."
                if touched_decoy else f"Flagged session, score {score:.3f} — awaiting analyst review."
            ),
            source=source,
            top_features=top_features or [],
            human_confirmed=touched_decoy,   # oracle labels are auto-confirmed
            canary_id=canary_id,
        )
        self._candidates[cand.incident_id] = cand
        return cand

    def record_user_feedback(self, item_id: str, helpful: bool, topic: str) -> None:
        """Fold AI thumbs-up/down feedback into the adaptation signal."""
        # Down-votes on clinical answers become review candidates for prompt/model tuning.
        if not helpful:
            self._candidates[f"fb_{item_id}"] = RetrainingCandidate(
                incident_id=f"fb_{item_id}",
                tier="Low",
                explanation=f"User marked an AI answer unhelpful (topic: {topic}).",
                source=LabelSource.USER_FEEDBACK,
            )

    # ── poisoning quarantine ────────────────────────────────────────────────────
    def _baseline_high_fraction(self, baseline: Dict[str, int]) -> float:
        total = sum(baseline.values()) or 1
        return baseline.get("High", 0) / total

    def run_poisoning_check(self, baseline_distribution: Dict[str, int]) -> List[str]:
        """
        Flag analyst-labelled candidates that would suspiciously normalise attacks.
        Returns the list of quarantined incident_ids. Mirage/oracle labels exempt.
        """
        pending = [c for c in self._candidates.values() if not c.human_confirmed and c.source != LabelSource.MIRAGE_ORACLE]
        if not pending:
            return []

        baseline_high = self._baseline_high_fraction(baseline_distribution)
        batch_high = sum(1 for c in pending if c.tier == "High") / max(len(pending), 1)

        quarantined: List[str] = []
        if baseline_high > 0.15 and batch_high < (baseline_high - POISON_DRIFT_THRESHOLD):
            for c in pending:
                if c.tier == "Low":
                    c.quarantined = True
                    c.quarantine_reason = (
                        f"Batch would drop High-tier fraction from {baseline_high:.0%} "
                        f"to {batch_high:.0%} (>{int(POISON_DRIFT_THRESHOLD*100)}% shift) — possible label poisoning."
                    )
                    quarantined.append(c.incident_id)
            if quarantined:
                logger.warning("secops_poison_quarantine count=%d", len(quarantined))
        return quarantined

    # ── HITL approval ───────────────────────────────────────────────────────────
    def approve(self, incident_id: str, override_quarantine: bool = False) -> bool:
        c = self._candidates.get(incident_id)
        if not c:
            return False
        if c.quarantined and not override_quarantine:
            logger.warning("secops_approve_blocked_by_quarantine id=%s", incident_id)
            return False
        c.human_confirmed = True
        return True

    def confirmed_labels(self) -> List[RetrainingCandidate]:
        """The clean, confirmed training set ready to feed a retraining job."""
        return [c for c in self._candidates.values() if c.human_confirmed and not c.quarantined]

    def stats(self) -> Dict[str, int]:
        vals = list(self._candidates.values())
        return {
            "total": len(vals),
            "confirmed": sum(1 for c in vals if c.human_confirmed),
            "quarantined": sum(1 for c in vals if c.quarantined),
            "oracle": sum(1 for c in vals if c.source == LabelSource.MIRAGE_ORACLE),
        }
