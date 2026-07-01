"""
ai_services/guardrails/safety_validator.py

Deterministic safety layer — runs BEFORE and AFTER every LLM response.

This is the most important new piece in the clinical AI pipeline.
It catches two things that the LLM itself cannot reliably catch:
  1. Red flags in the INPUT that require immediate escalation regardless of AI response
  2. Dangerous or non-compliant content in the AI OUTPUT before it reaches the user

Design principle: deterministic code, not LLM-judged code.
We do NOT ask the LLM "is this safe?" — we check hard rules in code.
An LLM can be jailbroken or hallucinate; these checks cannot.

Integration point:
  ai_services/clinical_reasoning/llm_service.py
    → validate_input(user_text) BEFORE sending to model
    → validate_output(ai_response) BEFORE returning to frontend
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class EscalationLevel(str, Enum):
    NONE = "none"
    CAUTION = "caution"       # Flag to clinician; do not block response
    WARNING = "warning"       # Prepend prominent warning to response
    BLOCK = "block"           # Do not send AI response; return escalation instruction instead
    EMERGENCY = "emergency"   # Display emergency-services instruction immediately


@dataclass
class InputValidationResult:
    escalation_level: EscalationLevel
    red_flags: List[str] = field(default_factory=list)
    emergency_message: Optional[str] = None
    allow_ai_response: bool = True


@dataclass
class OutputValidationResult:
    safe: bool
    modified_content: Optional[str] = None   # Cleaned/prepended content
    violations: List[str] = field(default_factory=list)
    escalation_level: EscalationLevel = EscalationLevel.NONE


class SafetyValidator:
    """
    Deterministic rule-based safety validator.
    Stateless; instantiate once and reuse.
    """

    # ── Emergency keywords — immediate escalation regardless of context ────────
    _EMERGENCY_PATTERNS = [
        (re.compile(r"\b(chest pain|chest tightness)\b.{0,50}\b(radiating|jaw|arm|sweating|dizzy)\b", re.I), "Possible cardiac event — chest pain with radiation/diaphoresis"),
        (re.compile(r"\b(can'?t breathe|cannot breathe|not breathing|stopped breathing|breath.{0,10}stopped)\b", re.I), "Respiratory distress / arrest"),
        (re.compile(r"\b(unconscious|unresponsive|passed out|won'?t wake)\b", re.I), "Loss of consciousness"),
        (re.compile(r"\b(seiz(ure|ing)|convuls)\b", re.I), "Seizure activity"),
        (re.compile(r"\b(stroke|facial droop|arm weakness|slurred speech)\b", re.I), "Possible stroke symptoms (FAST)"),
        (re.compile(r"\b(suicid|kill (my|him|her)self|end(ing)? (my|their) life|self.harm)\b", re.I), "Suicidal ideation / self-harm"),
        (re.compile(r"\b(anaphyl|face.{0,15}(swelling|swollen)|throat.{0,20}closing|epipen)\b", re.I), "Possible anaphylaxis"),
        (re.compile(r"\b(severe bleeding|blood.{0,10}(pouring|spurting|won'?t stop))\b", re.I), "Severe haemorrhage"),
        (re.compile(r"\b(overdose|od'?d|took too many)\b", re.I), "Possible overdose"),
        (re.compile(r"\b(meningitis|stiff neck|rash.{0,20}(doesn'?t fade|glass test|non.blanch))\b", re.I), "Possible meningococcal sepsis"),
    ]

    # ── Red-flag clinical features — prepend to response, don't block ─────────
    _RED_FLAG_PATTERNS = [
        (re.compile(r"\b(weight loss.{0,30}unintentional|losing weight without trying)\b", re.I), "Unexplained weight loss — malignancy / chronic disease workup"),
        (re.compile(r"\b(night sweats|drenching.{0,10}night)\b", re.I), "Night sweats — TB / lymphoma / endocrine workup"),
        (re.compile(r"\b(haemoptysis|coughing.{0,10}blood|blood.{0,10}cough)\b", re.I), "Haemoptysis — urgent respiratory workup"),
        (re.compile(r"\b(blood.{0,10}(urine|stool|vomit)|melaena|haematuria)\b", re.I), "Blood in excretions — urgent investigation"),
        (re.compile(r"\b(papilloedema|sudden.{0,10}(severe|worst).{0,10}headache|thunderclap)\b", re.I), "Thunderclap / papilloedema — subarachnoid haemorrhage?"),
        (re.compile(r"\b(high fever.{0,30}(rash|petechiae|purpura))\b", re.I), "Fever + rash — sepsis / meningococcal evaluation"),
        (re.compile(r"\bkidney.{0,10}pain.{0,30}(fever|rigor|shiver)\b", re.I), "Loin pain + fever — pyelonephritis / urosepsis"),
    ]

    # ── Output content violations ──────────────────────────────────────────────
    _OUTPUT_VIOLATIONS = [
        # The model must not claim to diagnose
        (re.compile(r"\byou (definitely|certainly|definitely) have\b", re.I),
         "Model appears to make a definitive diagnosis claim"),
        # Must not prescribe specific drug doses
        (re.compile(r"\btake \d+\s*(mg|mcg|ml|units?)\b.{0,30}\b(metformin|warfarin|insulin|digoxin|lithium)\b", re.I),
         "Specific high-risk drug dosing instruction"),
        # Must not tell the user to ignore a clinician's recommendation
        (re.compile(r"\b(ignore|disregard|don'?t listen to).{0,30}(doctor|physician|clinician|specialist)\b", re.I),
         "Instruction to ignore medical professional"),
        # Suicide / self-harm method content
        (re.compile(r"\b(how to.{0,20}(kill|harm|hurt).{0,20}(yourself|himself|herself))\b", re.I),
         "Self-harm method content"),
    ]

    _EMERGENCY_INSTRUCTION = (
        "⚠️ EMERGENCY DETECTED ⚠️\n\n"
        "Based on the symptoms described, this may be a medical emergency.\n\n"
        "**Call emergency services immediately: 112 (India) / 999 / 911**\n\n"
        "Do not wait for an AI response. If the person is unconscious and not breathing, "
        "begin CPR if you are trained to do so.\n\n"
        "Once the emergency is managed, return to this app for follow-up guidance."
    )

    def validate_input(self, user_text: str, is_clinician: bool = False) -> InputValidationResult:
        """
        Check the user's input for emergency signals and clinical red flags.

        For clinicians: surface red flags as cautions, do not block.
        For consumers/public: surface emergencies prominently; block AI response.
        """
        # Emergency check — always runs first
        for pattern, description in self._EMERGENCY_PATTERNS:
            if pattern.search(user_text):
                level = EscalationLevel.CAUTION if is_clinician else EscalationLevel.EMERGENCY
                logger.warning(
                    "safety_validator emergency_pattern_matched description=%r is_clinician=%s",
                    description, is_clinician,
                )
                return InputValidationResult(
                    escalation_level=level,
                    red_flags=[description],
                    emergency_message=self._EMERGENCY_INSTRUCTION if not is_clinician else None,
                    allow_ai_response=is_clinician,  # Clinicians still get AI; public gets emergency only
                )

        # Red-flag check
        red_flags = []
        for pattern, description in self._RED_FLAG_PATTERNS:
            if pattern.search(user_text):
                red_flags.append(description)

        level = EscalationLevel.WARNING if red_flags else EscalationLevel.NONE
        return InputValidationResult(
            escalation_level=level,
            red_flags=red_flags,
            allow_ai_response=True,
        )

    def validate_output(self, ai_response_text: str) -> OutputValidationResult:
        """
        Check the AI's response for content violations before displaying to user.

        If a violation is found: either clean the response or block it,
        depending on severity.
        """
        violations = []
        for pattern, description in self._OUTPUT_VIOLATIONS:
            if pattern.search(ai_response_text):
                violations.append(description)
                logger.warning("safety_validator output_violation description=%r", description)

        if not violations:
            return OutputValidationResult(safe=True)

        # For now: prepend a disclaimer and still return the response.
        # For suicide/self-harm violations: block entirely.
        has_blocking_violation = any("self-harm" in v for v in violations)
        if has_blocking_violation:
            return OutputValidationResult(
                safe=False,
                modified_content=(
                    "I'm unable to provide a response to this query. "
                    "If you or someone you know is in distress, please call iCall at 9152987821 "
                    "or Vandrevala Foundation Helpline at 1860-2662-345 (India, 24/7)."
                ),
                violations=violations,
                escalation_level=EscalationLevel.BLOCK,
            )

        disclaimer = (
            "⚠️ Clinical AI Disclaimer: This response is for clinical decision support only. "
            "Final diagnostic and treatment decisions must be made by a qualified clinician.\n\n"
        )
        return OutputValidationResult(
            safe=False,
            modified_content=disclaimer + ai_response_text,
            violations=violations,
            escalation_level=EscalationLevel.WARNING,
        )

    def build_red_flag_prefix(self, red_flags: List[str]) -> str:
        """Render red flags as a visible prefix for the AI response."""
        if not red_flags:
            return ""
        lines = ["🚨 **Clinical Red Flags Detected:**"]
        for flag in red_flags:
            lines.append(f"  • {flag}")
        lines.append("\nPlease ensure these are addressed in your assessment.\n\n---\n\n")
        return "\n".join(lines)
