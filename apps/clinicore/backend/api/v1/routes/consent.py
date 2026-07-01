"""
apps/clinicore/backend/api/v1/routes/consent.py

Clinic-side consent endpoints: request and verify consent before a clinician
can pull a patient's record into a consultation. Patients grant/revoke their
own consent primarily through the RelayMed app (see apps/relaymed/backend);
this surface is read-mostly plus the one clinic-initiated action
(requesting consent at intake, e.g. for a new walk-in patient).
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apps.clinicore.backend.core.dependencies import get_consent_manager
from apps.clinicore.backend.core.security import AuthenticatedUser, require_clinician
from substrate.consent.models import (
    CollectionMethod,
    ConsentPurpose,
    ConsentSummary,
    DataCategory,
)
from substrate.consent.service import (
    ConsentManager,
    ConsentNotFoundError,
    SensitiveCategoryConsentError,
)

router = APIRouter(prefix="/patients/{patient_id}/consent", tags=["consent"])


@router.get("", response_model=List[ConsentSummary])
async def list_patient_consents(
    patient_id: str,
    user: AuthenticatedUser = Depends(require_clinician),
    consent_manager: ConsentManager = Depends(get_consent_manager),
):
    records = await consent_manager.list_consents(patient_id)
    return [
        ConsentSummary(
            consent_id=r.consent_id,
            purpose=r.purpose,
            purpose_description=r.purpose_description,
            data_categories=r.data_categories,
            fiduciary_name=r.data_fiduciary_name,
            granted_at=r.granted_at,
            expires_at=r.expires_at,
            status=r.status,
            delegated_to_name=r.delegated_to_name,
            delegation_relationship=r.delegation_relationship,
        )
        for r in records
    ]


@router.post("/request-clinical-decision-support", status_code=status.HTTP_201_CREATED)
async def request_clinical_decision_support_consent(
    patient_id: str,
    request: Request,
    consent_text_version: str,
    user: AuthenticatedUser = Depends(require_clinician),
    consent_manager: ConsentManager = Depends(get_consent_manager),
):
    """
    Records consent collected verbally/in-app at intake (CollectionMethod.APP_UI
    or VERBAL_WITNESSED). The clinic is the data fiduciary; the patient must
    have separately confirmed the consent text shown on the intake screen —
    this endpoint is the *recording* of that consent, not the collection UI.
    """
    if user.clinic_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token has no clinic association")

    from substrate.consent.models import ConsentGrant  # local import avoids route-module bloat

    grant = ConsentGrant(
        data_principal_id=patient_id,
        data_fiduciary_id=user.clinic_id,
        data_fiduciary_name=user.clinic_id,
        purpose=ConsentPurpose.CLINICAL_DECISION_SUPPORT,
        data_categories=[DataCategory.CONDITIONS, DataCategory.CHAT_HISTORY, DataCategory.MEDICATIONS],
        collection_method=CollectionMethod.APP_UI,
        consent_text_version=consent_text_version,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown"),
    )

    try:
        record = await consent_manager.grant_consent(grant)
    except SensitiveCategoryConsentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return {"consent_id": record.consent_id, "status": record.status.value}
