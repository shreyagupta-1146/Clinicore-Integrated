"""
apps/relaymed/backend/api/v1/routes/medications.py

Medication management and adherence logging.

POST /medications/log       — log a dose taken / missed / skipped
GET  /medications           — list current medications
GET  /medications/adherence — weekly adherence summary per medication

The adherence score drives the caregiver alert logic and the longitudinal
risk model (ai_services/longitudinal/).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from apps.relaymed.backend.core.dependencies import (
    get_audit_logger,
    get_consent_manager,
    get_current_user_id,
    get_fhir_timeline,
)
from apps.relaymed.backend.rules.adherence import AdherenceStatus, compute_adherence_score
from substrate.audit.models import AuditEvent, AuditEventType
from substrate.audit.service import AuditLogger
from substrate.consent.models import ConsentPurpose, DataCategory
from substrate.consent.service import ConsentManager
from substrate.fhir.timeline import FHIRTimeline

router = APIRouter()


class DoseLog(BaseModel):
    medication_id: str
    medication_name: str
    status: str = Field(..., description="taken | missed | skipped | delayed")
    scheduled_time: str   # ISO8601
    actual_time: Optional[str] = None
    notes: Optional[str] = None


class DoseLogResponse(BaseModel):
    observation_id: str
    adherence_status: str


class AdherenceSummary(BaseModel):
    medication_id: str
    medication_name: str
    period_days: int
    doses_scheduled: int
    doses_taken: int
    adherence_pct: float
    status: str


@router.post("/log", response_model=DoseLogResponse, status_code=status.HTTP_201_CREATED)
async def log_dose(
    dose: DoseLog,
    user_id: Annotated[str, Depends(get_current_user_id)],
    consent_manager: Annotated[ConsentManager, Depends(get_consent_manager)],
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    check = await consent_manager.check_consent(
        data_principal_id=user_id,
        requesting_entity_id="relaymed-medication-service",
        purpose=ConsentPurpose.MEDICATION_ADHERENCE,
        data_categories=[DataCategory.MEDICATIONS],
    )
    if not check.permitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=check.denial_reason)

    fhir_observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey"}]}],
        "code": {"text": f"Medication adherence: {dose.medication_name}"},
        "subject": {"reference": f"Patient/{user_id}"},
        "effectiveDateTime": dose.actual_time or dose.scheduled_time,
        "valueString": dose.status,
        "note": [{"text": dose.notes}] if dose.notes else [],
        "extension": [{"url": "medication_id", "valueString": dose.medication_id}],
    }
    obs_id = await fhir_timeline.add_observation(fhir_observation)

    await audit_logger.log(AuditEvent(
        event_type=AuditEventType.MEDICATION_LOGGED,
        actor_id=user_id,
        resource_type="MedicationAdherence",
        resource_id=dose.medication_id,
        details={"status": dose.status},
    ))

    return DoseLogResponse(observation_id=obs_id, adherence_status=dose.status)


@router.get("", response_model=List[dict])
async def list_medications(
    user_id: Annotated[str, Depends(get_current_user_id)],
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
):
    return await fhir_timeline.get_medications(patient_id=user_id, status="active")


@router.get("/adherence", response_model=List[AdherenceSummary])
async def get_adherence_summary(
    user_id: Annotated[str, Depends(get_current_user_id)],
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
    days: int = 7,
):
    observations = await fhir_timeline.get_observations(patient_id=user_id, category="survey", max_count=500)
    adherence_obs = [o for o in observations if "Medication adherence" in o.get("code", {}).get("text", "")]
    return compute_adherence_score(observations=adherence_obs, period_days=days)
