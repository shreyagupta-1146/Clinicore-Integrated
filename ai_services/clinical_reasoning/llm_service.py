"""
ai_services/clinical_reasoning/llm_service.py

ClinicalReasoningService — the orchestrator for every AI-assisted clinical
interaction in Clinicore. This is the one place all the safety machinery
is wired together. Routes do not call ModelGateway directly; they call this.

Pipeline (every call, no exceptions):
  1. check_consent()        — DPDP gate; refuse if not permitted
  2. validate_input()        — deterministic emergency/red-flag scan
  3. retrieve research        — PubMed grounding sources
  4. gateway.complete()       — hybrid-routed LLM call (cloud de-identified / on-prem raw)
  5. grounding check          — verify citations against retrieved sources
  6. validate_output()        — deterministic content-safety scan
  7. audit log                — every step, win or lose
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from substrate.audit.models import AuditEvent, AuditEventType
from substrate.audit.service import AuditLogger
from substrate.consent.models import ConsentPurpose, DataCategory
from substrate.consent.service import ConsentManager
from substrate.model_gateway.router import GatewayResponse, ModelGateway

from ai_services.clinical_reasoning.research_retrieval import ResearchRetriever, ResearchSource
from ai_services.guardrails.grounding_enforcer import (
    GROUNDING_SYSTEM_PROMPT_ADDENDUM,
    GroundingEnforcer,
    GroundingReport,
)
from ai_services.guardrails.safety_validator import (
    EscalationLevel,
    SafetyValidator,
)

logger = logging.getLogger(__name__)

_BASE_SYSTEM_PROMPT = """You are a clinical decision-support assistant used by licensed clinicians.
You do NOT replace clinical judgement. You surface relevant information, differential
considerations, and research context to support — never to dictate — the clinician's decision.

Rules:
- Never state a definitive diagnosis. Use language like "consistent with" or "consider".
- Never give a specific drug dose for high-risk medications (insulin, warfarin, digoxin, lithium, opioids).
- Always note when evidence is limited, conflicting, or based on a small/old study.
- If the clinician's query suggests an emergency, say so plainly and recommend immediate escalation.
"""


@dataclass
class ClinicalReasoningResult:
    response_text: str
    sources: List[ResearchSource]
    grounding_report: Optional[GroundingReport]
    escalation_level: EscalationLevel
    red_flags: List[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: Optional[str] = None
    route_used: Optional[str] = None
    model_used: Optional[str] = None
    latency_ms: Optional[int] = None


class ClinicalReasoningService:
    def __init__(
        self,
        gateway: ModelGateway,
        consent_manager: ConsentManager,
        audit_logger: AuditLogger,
        research_retriever: ResearchRetriever,
        safety_validator: Optional[SafetyValidator] = None,
        grounding_enforcer: Optional[GroundingEnforcer] = None,
    ):
        self._gateway = gateway
        self._consent = consent_manager
        self._audit = audit_logger
        self._research = research_retriever
        self._safety = safety_validator or SafetyValidator()
        self._grounding = grounding_enforcer or GroundingEnforcer()

    async def ask(
        self,
        *,
        patient_id: str,
        clinician_id: str,
        clinic_id: str,
        query_text: str,
        conversation_history: Optional[List[Dict]] = None,
        ip_address: str,
        is_clinician: bool = True,
    ) -> ClinicalReasoningResult:
        # ── 1. Consent gate ──────────────────────────────────────────────────
        consent_result = await self._consent.check_consent(
            data_principal_id=patient_id,
            requesting_entity_id=clinic_id,
            purpose=ConsentPurpose.CLINICAL_DECISION_SUPPORT,
            data_categories=[DataCategory.CONDITIONS, DataCategory.CHAT_HISTORY],
        )
        if not consent_result.permitted:
            await self._audit.log(AuditEvent(
                event_type=AuditEventType.CONSENT_CHECKED_DENIED,
                actor_id=clinician_id,
                resource_type="clinical_chat",
                resource_id=patient_id,
                details={"reason": consent_result.denial_reason},
                ip_address=ip_address,
            ))
            return ClinicalReasoningResult(
                response_text="",
                sources=[],
                grounding_report=None,
                escalation_level=EscalationLevel.NONE,
                blocked=True,
                block_reason=consent_result.denial_reason or "Consent not granted for this purpose.",
            )

        await self._audit.log(AuditEvent(
            event_type=AuditEventType.CLINICAL_MESSAGE_SENT,
            actor_id=clinician_id,
            resource_type="patient",
            resource_id=patient_id,
            details={"query_length": len(query_text)},
            ip_address=ip_address,
            authorising_consent_id=consent_result.consent_id,
        ))

        # ── 2. Deterministic input safety scan ──────────────────────────────
        input_check = self._safety.validate_input(query_text, is_clinician=is_clinician)

        if input_check.escalation_level == EscalationLevel.EMERGENCY:
            return ClinicalReasoningResult(
                response_text=input_check.emergency_message or "",
                sources=[],
                grounding_report=None,
                escalation_level=EscalationLevel.EMERGENCY,
                red_flags=input_check.red_flags,
                blocked=True,
                block_reason="emergency_detected",
            )

        if not input_check.allow_ai_response:
            return ClinicalReasoningResult(
                response_text="",
                sources=[],
                grounding_report=None,
                escalation_level=input_check.escalation_level,
                red_flags=input_check.red_flags,
                blocked=True,
                block_reason="ai_response_withheld",
            )

        # ── 3. Research retrieval (grounding sources) ───────────────────────
        sources = await self._research.search(query_text)
        research_context = self._research.format_for_prompt(sources)
        available_source_ids = {s.source_id for s in sources}

        system_prompt = (
            _BASE_SYSTEM_PROMPT
            + "\n"
            + GROUNDING_SYSTEM_PROMPT_ADDENDUM
            + "\n"
            + research_context
        )

        red_flag_prefix = self._safety.build_red_flag_prefix(input_check.red_flags)

        # ── 4. Hybrid-routed LLM call ────────────────────────────────────────
        gateway_response: GatewayResponse = await self._gateway.complete(
            system_prompt=system_prompt,
            user_text=query_text,
            conversation_history=conversation_history,
        )

        # ── 5. Grounding verification ────────────────────────────────────────
        grounding_report = self._grounding.check(gateway_response.content, available_source_ids)
        annotated_text = self._grounding.annotate_unverified(gateway_response.content, grounding_report)

        # ── 6. Deterministic output safety scan ──────────────────────────────
        output_check = self._safety.validate_output(annotated_text)
        final_text = output_check.modified_content if not output_check.safe else annotated_text
        final_text = red_flag_prefix + final_text

        # ── 7. Audit the AI response ─────────────────────────────────────────
        await self._audit.log(AuditEvent(
            event_type=AuditEventType.CLINICAL_AI_RESPONSE,
            actor_id=clinician_id,
            resource_type="patient",
            resource_id=patient_id,
            details={
                "route_used": gateway_response.route_used.value,
                "model_used": gateway_response.model_used,
                "phi_risk_score": gateway_response.phi_risk_score,
                "grounding_score": grounding_report.grounding_score,
                "unverified_citations": grounding_report.unverified_citations,
                "output_violations": output_check.violations,
                "latency_ms": gateway_response.latency_ms,
            },
            ip_address=ip_address,
            authorising_consent_id=consent_result.consent_id,
        ))

        return ClinicalReasoningResult(
            response_text=final_text,
            sources=sources,
            grounding_report=grounding_report,
            escalation_level=output_check.escalation_level,
            red_flags=input_check.red_flags,
            blocked=False,
            route_used=gateway_response.route_used.value,
            model_used=gateway_response.model_used,
            latency_ms=gateway_response.latency_ms,
        )
