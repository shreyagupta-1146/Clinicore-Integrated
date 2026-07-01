"""
ai_services/guardrails/grounding_enforcer.py

Grounding enforcement — "cite or flag uncertainty."

Every clinical claim the AI makes must either:
  (a) be traceable to a RAG-retrieved source (PubMed citation), or
  (b) be explicitly flagged as a general-knowledge / uncertain statement

This does NOT eliminate hallucination. It makes hallucination VISIBLE
to the clinician reading the output, which is the realistic, achievable goal.

How it works:
  1. The LLM is instructed (via system prompt) to tag claims with [CITED] or [GENERAL]
  2. This module parses those tags and verifies [CITED] claims actually reference
     a source that was in the RAG context provided to the model
  3. Any [CITED] tag that does NOT match a provided source is downgraded to
     [UNVERIFIED] and flagged — this catches citation hallucination
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Set

logger = logging.getLogger(__name__)

_CITATION_TAG_PATTERN = re.compile(r"\[CITED:\s*([A-Za-z0-9_\-]+)\]")
_GENERAL_TAG_PATTERN = re.compile(r"\[GENERAL\]")


@dataclass
class GroundingReport:
    total_claims: int
    cited_claims: int
    general_claims: int
    unverified_citations: List[str] = field(default_factory=list)
    untagged_sentences: List[str] = field(default_factory=list)
    grounding_score: float = 0.0   # cited_verified / total_claims


class GroundingEnforcer:
    """
    Parses LLM output for citation tags and verifies them against the
    RAG source set that was actually provided in context.
    """

    def check(self, ai_response_text: str, available_source_ids: Set[str]) -> GroundingReport:
        cited_matches = _CITATION_TAG_PATTERN.findall(ai_response_text)
        general_matches = _GENERAL_TAG_PATTERN.findall(ai_response_text)

        unverified = [cid for cid in cited_matches if cid not in available_source_ids]

        # Sentences containing a clinical claim verb but no tag at all
        # (heuristic — production should use sentence-level NLI/claim extraction)
        untagged = self._find_untagged_claim_sentences(ai_response_text)

        total = len(cited_matches) + len(general_matches) + len(untagged)
        verified_cited = len(cited_matches) - len(unverified)
        grounding_score = (verified_cited / total) if total > 0 else 1.0

        if unverified:
            logger.warning(
                "grounding_enforcer unverified_citations=%s — possible citation hallucination",
                unverified,
            )

        return GroundingReport(
            total_claims=total,
            cited_claims=len(cited_matches),
            general_claims=len(general_matches),
            unverified_citations=unverified,
            untagged_sentences=untagged,
            grounding_score=grounding_score,
        )

    def annotate_unverified(self, ai_response_text: str, report: GroundingReport) -> str:
        """Replace unverified [CITED: x] tags with a visible [UNVERIFIED] marker."""
        result = ai_response_text
        for source_id in report.unverified_citations:
            result = result.replace(
                f"[CITED: {source_id}]",
                f"[⚠️ UNVERIFIED CITATION — could not confirm source {source_id}]",
            )
        return result

    def _find_untagged_claim_sentences(self, text: str) -> List[str]:
        """
        Heuristic: sentences with strong clinical-claim verbs that lack any tag.
        This is intentionally conservative (low recall, low false-positive rate)
        because it drives a visible warning shown to clinicians.
        """
        claim_verbs = r"\b(indicates|suggests|confirms|demonstrates|shows|proves|is associated with|causes|increases the risk of)\b"
        sentences = re.split(r"(?<=[.!?])\s+", text)
        untagged = []
        for sentence in sentences:
            if re.search(claim_verbs, sentence, re.I):
                if not _CITATION_TAG_PATTERN.search(sentence) and not _GENERAL_TAG_PATTERN.search(sentence):
                    untagged.append(sentence.strip())
        return untagged


GROUNDING_SYSTEM_PROMPT_ADDENDUM = """
## Grounding Requirement
For every clinical claim you make (e.g., "X is associated with Y", "X increases risk of Y"):
- If the claim is directly supported by a source in the provided research context, tag it: [CITED: <source_id>]
- If the claim is general medical knowledge not tied to a specific provided source, tag it: [GENERAL]
Do not state a [CITED] tag unless the source_id matches one of the IDs given to you in the
research context block. Fabricating a citation is a critical failure.
"""
