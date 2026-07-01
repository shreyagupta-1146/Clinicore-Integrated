"""
apps/relaymed/backend/api\v1\routes\vitals.py

Vital sign ingestion (wearable / manual entry) and retrieval.

POST /vitals          — ingest one reading
GET  /vitals/{metric} — retrieve history for a metric

Consent required: WELLNESS_TRACKING on DataCategory.VITALS.
Every ingest writes a FHIR Observation; anomaly rules fire async.
"""

from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from apps.relaymed.backend.core.dependencies import (
    get_audit_logger,
    get_consent_manager,
    get_current_user_id,
    get_fhir_timeline,
)
from apps.relaymed.backend.services.vitals_service import VitalsService
from substrate.audit.service import AuditLogger
from substrate.consent.service import ConsentManager
from substrate.fhir.timeline import FHIRTimeline

router = APIRouter()


class VitalReading(BaseModel):
    metric: str = Field(..., description="e.g. heart_rate, blood_pressure_systolic, spo2")
    value: float
    unit: str
    recorded_at: Optional[str] = None   # ISO8601; defaults to now if omitted
    source: str = Field(default="manual", description="manual | fitbit | health_connect | omron")


class VitalResponse(BaseModel):
    observation_id: str
    anomaly_detected: bool
    severity: Optional[str] = None


@router.post("", response_model=VitalResponse, status_code=status.HTTP_201_CREATED)
async def ingest_vital(
    reading: VitalReading,
    user_id: Annotated[str, Depends(get_current_user_id)],
    consent_manager: Annotated[ConsentManager, Depends(get_consent_manager)],
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    svc = VitalsService(
        consent_manager=consent_manager,
        fhir_timeline=fhir_timeline,
        audit_logger=audit_logger,
    )
    try:
        result = await svc.ingest(
            patient_id=user_id,
            metric=reading.metric,
            value=reading.value,
            unit=reading.unit,
            recorded_at=reading.recorded_at,
            source=reading.source,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return VitalResponse(
        observation_id=result["observation_id"],
        anomaly_detected=result["anomaly_detected"],
        severity=result.get("severity"),
    )


@router.get("/{metric}", response_model=List[dict])
async def get_vital_history(
    metric: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
    limit: int = 50,
):
    observations = await fhir_timeline.get_observations(
        patient_id=user_id,
        category="vital-signs",
        max_count=limit,
    )
    # Filter client-side by metric code
    return [o for o in observations if _matches_metric(o, metric)]


def _matches_metric(observation: dict, metric: str) -> bool:
    code_obj = observation.get("code", {})
    codings = code_obj.get("coding", [])
    text = code_obj.get("text", "").lower()
    return metric.lower() in text or any(
        metric.lower() in c.get("display", "").lower() for c in codings
    )
