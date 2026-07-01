"""
apps/clinicore/backend/api/v1/routes/consultations.py

The core Clinicore product surface: a clinician asks a question about a
patient, and gets a hybrid-routed, grounded, safety-checked AI response.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.clinicore.backend.core.config import ClinicoreSettings, get_settings
from apps.clinicore.backend.core.dependencies import get_clinical_reasoning_service
from apps.clinicore.backend.core.security import AuthenticatedUser, require_clinician
from apps.clinicore.backend.schemas.consultation import AskRequest, AskResponse, ResearchSourceOut
from apps.clinicore.backend.services.consultation_service import (
    ConsultationService,
    ContinuationDepthExceededError,
    MessageLimitExceededError,
)
from ai_services.clinical_reasoning.llm_service import ClinicalReasoningService
from substrate.db.base import get_db

router = APIRouter(prefix="/patients/{patient_id}/consultations", tags=["consultations"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    patient_id: str,
    body: AskRequest,
    request: Request,
    user: AuthenticatedUser = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
    reasoning_service: ClinicalReasoningService = Depends(get_clinical_reasoning_service),
    settings: ClinicoreSettings = Depends(get_settings),
) -> AskResponse:
    if user.clinic_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token has no clinic association")

    service = ConsultationService(
        db=db,
        reasoning_service=reasoning_service,
        max_messages_per_chat=settings.max_messages_per_chat,
        max_continuation_depth=settings.max_continuation_depth,
    )

    try:
        session, assistant_message, result = await service.ask(
            patient_id=patient_id,
            clinician_id=user.user_id,
            clinic_id=user.clinic_id,
            query_text=body.query_text,
            session_id=body.session_id,
            ip_address=request.client.host if request.client else "unknown",
        )
    except MessageLimitExceededError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    if result.blocked:
        return AskResponse(
            session_id=session.session_id,
            message_id=assistant_message.message_id,
            response_text=result.response_text,
            sources=[],
            grounding_score=None,
            escalation_level=result.escalation_level.value,
            red_flags=result.red_flags,
            blocked=True,
            block_reason=result.block_reason,
            route_used=None,
            model_used=None,
            latency_ms=None,
        )

    return AskResponse(
        session_id=session.session_id,
        message_id=assistant_message.message_id,
        response_text=result.response_text,
        sources=[
            ResearchSourceOut(
                source_id=s.source_id, title=s.title, journal=s.journal,
                pub_year=s.pub_year, url=s.url,
            )
            for s in result.sources
        ],
        grounding_score=(result.grounding_report.grounding_score if result.grounding_report else None),
        escalation_level=result.escalation_level.value,
        red_flags=result.red_flags,
        blocked=False,
        block_reason=None,
        route_used=result.route_used,
        model_used=result.model_used,
        latency_ms=result.latency_ms,
    )


@router.post("/{session_id}/continue", status_code=status.HTTP_201_CREATED)
async def continue_session(
    patient_id: str,
    session_id: str,
    user: AuthenticatedUser = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
    reasoning_service: ClinicalReasoningService = Depends(get_clinical_reasoning_service),
    settings: ClinicoreSettings = Depends(get_settings),
):
    if user.clinic_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token has no clinic association")

    service = ConsultationService(
        db=db,
        reasoning_service=reasoning_service,
        max_messages_per_chat=settings.max_messages_per_chat,
        max_continuation_depth=settings.max_continuation_depth,
    )
    try:
        new_session = await service.start_continuation(
            parent_session_id=session_id,
            patient_id=patient_id,
            clinician_id=user.user_id,
            clinic_id=user.clinic_id,
        )
    except ContinuationDepthExceededError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    return {"session_id": new_session.session_id}
