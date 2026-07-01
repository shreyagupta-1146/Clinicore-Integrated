"""
apps/relaymed/backend/api/v1/routes/wellness.py

Wellness / lifestyle tracking: sleep, activity, stress self-report.

GET  /wellness/summary   — 7-day wellness summary
POST /wellness/log       — log a wellness data point

Consent required: WELLNESS_TRACKING on DataCategory.LIFESTYLE.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.relaymed.backend.core.dependencies import (
    get_consent_manager,
    get_current_user_id,
    get_fhir_timeline,
)
from substrate.consent.models import ConsentPurpose, DataCategory
from substrate.consent.service import ConsentManager
from substrate.fhir.timeline import FHIRTimeline

router = APIRouter()


class WellnessLog(BaseModel):
    category: str   # sleep | activity | stress | nutrition | hydration
    value: float
    unit: str
    notes: Optional[str] = None


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def log_wellness(
    log: WellnessLog,
    user_id: Annotated[str, Depends(get_current_user_id)],
    consent_manager: Annotated[ConsentManager, Depends(get_consent_manager)],
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
):
    check = await consent_manager.check_consent(
        data_principal_id=user_id,
        requesting_entity_id="relaymed-wellness-service",
        purpose=ConsentPurpose.WELLNESS_TRACKING,
        data_categories=[DataCategory.LIFESTYLE],
    )
    if not check.permitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=check.denial_reason)

    observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey"}]}],
        "code": {"text": f"Wellness: {log.category}"},
        "subject": {"reference": f"Patient/{user_id}"},
        "valueQuantity": {"value": log.value, "unit": log.unit},
        "note": [{"text": log.notes}] if log.notes else [],
    }
    obs_id = await fhir_timeline.add_observation(observation)
    return {"observation_id": obs_id}


@router.get("/summary")
async def wellness_summary(
    user_id: Annotated[str, Depends(get_current_user_id)],
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
    days: int = 7,
):
    observations = await fhir_timeline.get_observations(patient_id=user_id, category="survey", max_count=200)
    wellness_obs = [o for o in observations if o.get("code", {}).get("text", "").startswith("Wellness:")]
    by_category: dict[str, list[float]] = {}
    for obs in wellness_obs:
        cat = obs.get("code", {}).get("text", "Wellness: unknown").replace("Wellness: ", "")
        val = obs.get("valueQuantity", {}).get("value")
        if val is not None:
            by_category.setdefault(cat, []).append(float(val))
    return {
        cat: {"avg": sum(vals) / len(vals), "count": len(vals)}
        for cat, vals in by_category.items()
    }
