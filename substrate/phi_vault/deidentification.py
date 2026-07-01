"""
platform/phi_vault/deidentification.py

PHI de-identification using Microsoft Presidio + safe-harbor field stripping.

This is the BOUNDARY GUARD for the hybrid sovereignty model:
  raw PHI → Presidio → residual-risk classifier → [permitted / blocked]
                                                        │
                                                 only if permitted
                                                        │
                                                        ▼
                                             cloud LLM (Claude, ZDR contract)

Two-stage pipeline:
  1. Presidio NER: detect and anonymise named entities (names, dates, IDs, etc.)
  2. Residual-risk classifier: catch what Presidio misses in rare/unusual presentations
     (e.g., "the only paediatrician in Nagercoil" is re-identifying even after NER)

Important limitation acknowledged here (not papered over):
  Perfect de-identification of clinical text is an UNSOLVED research problem.
  For rare conditions, even de-identified clinical detail can re-identify.
  This system routes high-risk cases to the on-prem model instead of cloud.
  The risk score threshold is configurable (PHI_RISK_THRESHOLD env var).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)

# ── Entities Presidio will detect and anonymise ───────────────────────────────
# Extend this list carefully; every entity type adds latency.
_PRESIDIO_ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "IP_ADDRESS",
    "DATE_TIME",        # DOB, appointment dates — keep relative age, strip absolute dates
    "LOCATION",         # City / hospital / address
    "IN_PAN",           # Indian PAN card
    "IN_AADHAAR",       # Aadhaar number
    "MEDICAL_LICENSE",  # Doctor registration numbers
    "URL",
    "NRP",              # National Registration / passport-like IDs
]

# ── Replacement tokens (what Presidio substitutes into the anonymised text) ───
_OPERATORS: dict[str, OperatorConfig] = {
    "PERSON":           OperatorConfig("replace", {"new_value": "[PATIENT]"}),
    "PHONE_NUMBER":     OperatorConfig("replace", {"new_value": "[PHONE]"}),
    "EMAIL_ADDRESS":    OperatorConfig("replace", {"new_value": "[EMAIL]"}),
    "IP_ADDRESS":       OperatorConfig("replace", {"new_value": "[IP]"}),
    "DATE_TIME":        OperatorConfig("replace", {"new_value": "[DATE]"}),
    "LOCATION":         OperatorConfig("replace", {"new_value": "[LOCATION]"}),
    "IN_PAN":           OperatorConfig("replace", {"new_value": "[PAN]"}),
    "IN_AADHAAR":       OperatorConfig("replace", {"new_value": "[AADHAAR]"}),
    "MEDICAL_LICENSE":  OperatorConfig("replace", {"new_value": "[LICENSE]"}),
    "URL":              OperatorConfig("replace", {"new_value": "[URL]"}),
    "NRP":              OperatorConfig("replace", {"new_value": "[ID]"}),
    "DEFAULT":          OperatorConfig("replace", {"new_value": "[REDACTED]"}),
}


@dataclass
class DeidentificationResult:
    original_text: str
    anonymised_text: str
    detected_entities: List[str]
    residual_risk_score: float   # 0.0 (safe to send to cloud) → 1.0 (must stay on-prem)
    routed_to_cloud: bool        # True = safe for cloud; False = on-prem only
    risk_reasons: List[str] = field(default_factory=list)


class DeidentificationService:
    """
    Presidio-based PHI de-identification with residual risk scoring.

    Initialisation loads the NLP model (en_core_web_lg by default).
    This is expensive; use a module-level singleton.
    """

    def __init__(self, phi_risk_threshold: float = 0.7):
        self._threshold = phi_risk_threshold
        nlp_config = {"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]}
        provider = NlpEngineProvider(nlp_configuration=nlp_config)
        self._analyzer = AnalyzerEngine(nlp_engine=provider.create_engine())
        self._anonymizer = AnonymizerEngine()

    def deidentify(self, text: str, language: str = "en") -> DeidentificationResult:
        """
        Run Presidio + residual risk classification.
        Returns the anonymised text and a routing decision.
        """
        # Stage 1: Presidio NER detection
        results: List[RecognizerResult] = self._analyzer.analyze(
            text=text,
            entities=_PRESIDIO_ENTITIES,
            language=language,
        )

        anonymised = self._anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=_OPERATORS,
        ).text

        detected = list({r.entity_type for r in results})

        # Stage 2: Residual risk scoring
        risk_score, risk_reasons = self._residual_risk_score(anonymised, detected)

        routed_to_cloud = risk_score < self._threshold

        if not routed_to_cloud:
            logger.info(
                "de-id residual_risk=%.2f threshold=%.2f → on-prem route reasons=%s",
                risk_score, self._threshold, risk_reasons,
            )

        return DeidentificationResult(
            original_text=text,
            anonymised_text=anonymised,
            detected_entities=detected,
            residual_risk_score=risk_score,
            routed_to_cloud=routed_to_cloud,
            risk_reasons=risk_reasons,
        )

    def _residual_risk_score(
        self, anonymised: str, detected_entities: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Heuristic residual re-identification risk scorer.

        This does NOT claim to be a rigorous k-anonymity or l-diversity check.
        It catches common patterns that increase re-identification risk:
        - Very rare conditions that are themselves identifying
        - Specific combination of location + condition + demographic
        - Unique institutional/procedural identifiers (e.g., "unit 3B, ward 12")
        - Direct ID leakage that Presidio might miss

        For production: replace the heuristics with a trained classifier
        fine-tuned on your clinical domain.
        """
        score = 0.0
        reasons: List[str] = []

        # Heuristic 1: Residual Aadhaar / PAN / phone-like patterns after anonymisation
        residual_id_patterns = [
            r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b",  # Aadhaar-like
            r"\b[A-Z]{5}\d{4}[A-Z]\b",          # PAN-like
            r"\b[6-9]\d{9}\b",                   # Indian mobile
        ]
        for pattern in residual_id_patterns:
            if re.search(pattern, anonymised):
                score += 0.4
                reasons.append(f"Residual ID pattern: {pattern}")

        # Heuristic 2: High-specificity rare-condition indicator phrases
        # These are conditions rare enough that the condition alone can re-identify.
        # List curated from clinical input; must be periodically updated.
        rare_condition_phrases = [
            "alpha-1 antitrypsin deficiency",
            "maple syrup urine disease",
            "tyrosinemia",
            "hutchinson-gilford progeria",
            "fibrodysplasia ossificans progressiva",
        ]
        lower = anonymised.lower()
        for phrase in rare_condition_phrases:
            if phrase in lower:
                score += 0.5
                reasons.append(f"Rare condition phrase: {phrase!r}")

        # Heuristic 3: Combination of specific location + condition after anonymisation
        if "[LOCATION]" not in anonymised and any(
            term in lower for term in ["district hospital", "primary health centre", "taluk"]
        ):
            score += 0.2
            reasons.append("Specific rural facility reference — potentially identifying")

        # Heuristic 4: Genetic data is always on-prem; never cloud.
        if any(kw in lower for kw in ["genetic", "genome", "dna", "chromosom", "mutation", "snp"]):
            score = max(score, 0.9)
            reasons.append("Genetic data — hard-routed to on-prem")

        return min(score, 1.0), reasons
