"""
apps/relaymed/backend/api/v1/routes/caregiver.py

Caregiver delegation API.

POST /caregiver/request                  — caregiver requests to monitor patient
POST /caregiver/{link_id}/approve        — patient approves (creates consent)
POST /caregiver/{link_id}/decline        — patient declines
GET  /caregiver/my-links                 — list links where I am the caregiver
GET  /caregiver/pending-requests         — list incoming requests where I am the patient
GET  /caregiver/{patient_id}/dashboard   — caregiver reads monitored patient's summary

DPDP Act 2023 constraint: only the data principal (patient) can approve.
Caregiver cannot self-grant access; the approve endpoint verifies the caller
is the principal, not the caregiver.
"""

from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.relaymed.backend.core.dependencies import (
    get_audit_logger,
    get_consent_manager,
    get_current_user_id,
    get_fhir_timeline,
)
from apps.relaymed.backend.modules.caregiver.service import CaregiverService
from substrate.audit.service import AuditLogger
from substrate.consent.service import ConsentManager
from substrate.db.base import get_db
from substrate.fhir.timeline import FHIRTimeline

router = APIRouter()


class CaregiverRequestPayload(BaseModel):
    patient_id: str
    visible_categories: List[str] = Field(
        default=["vitals", "medications"],
        description="Data categories the caregiver wants to see",
    )
    relationship: str = Field(default="CHILD_TO_PARENT", description="DelegationRelationship value")
    message: str = Field(default="", description="Optional message to patient")


class CaregiverLinkOut(BaseModel):
    link_id: str
    caregiver_id: str
    patient_id: str
    status: str
    visible_categories: List[str]
    relationship: str


@router.post("/request", response_model=CaregiverLinkOut, status_code=status.HTTP_201_CREATED)
async def request_caregiver_link(
    payload: CaregiverRequestPayload,
    caregiver_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    svc = CaregiverService(db=db, audit_logger=audit_logger, consent_manager=None)
    link = await svc.request_link(
        caregiver_id=caregiver_id,
        patient_id=payload.patient_id,
        visible_categories=payload.visible_categories,
        relationship=payload.relationship,
    )
    return CaregiverLinkOut(
        link_id=str(link.id),
        caregiver_id=link.caregiver_id,
        patient_id=link.patient_id,
        status=link.status.value,
        visible_categories=link.visible_categories,
        relationship=link.relationship.value,
    )


@router.post("/{link_id}/approve", response_model=CaregiverLinkOut)
async def approve_caregiver_link(
    link_id: str,
    patient_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    consent_manager: Annotated[ConsentManager, Depends(get_consent_manager)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    svc = CaregiverService(db=db, audit_logger=audit_logger, consent_manager=consent_manager)
    try:
        link = await svc.approve_link(link_id=link_id, approving_patient_id=patient_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return CaregiverLinkOut(
        link_id=str(link.id),
        caregiver_id=link.caregiver_id,
        patient_id=link.patient_id,
        status=link.status.value,
        visible_categories=link.visible_categories,
        relationship=link.relationship.value,
    )


@router.post("/{link_id}/decline")
async def decline_caregiver_link(
    link_id: str,
    patient_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    svc = CaregiverService(db=db, audit_logger=audit_logger, consent_manager=None)
    try:
        await svc.decline_link(link_id=link_id, declining_patient_id=patient_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return {"detail": "Caregiver request declined"}


@router.get("/my-links", response_model=List[CaregiverLinkOut])
async def list_my_caregiver_links(
    caregiver_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    svc = CaregiverService(db=db, audit_logger=audit_logger, consent_manager=None)
    links = await svc.list_caregiver_links(caregiver_id=caregiver_id)
    return [
        CaregiverLinkOut(
            link_id=str(l.id),
            caregiver_id=l.caregiver_id,
            patient_id=l.patient_id,
            status=l.status.value,
            visible_categories=l.visible_categories,
            relationship=l.relationship.value,
        )
        for l in links
    ]


@router.get("/pending-requests", response_model=List[CaregiverLinkOut])
async def list_pending_requests(
    patient_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    svc = CaregiverService(db=db, audit_logger=audit_logger, consent_manager=None)
    links = await svc.list_pending_for_patient(patient_id=patient_id)
    return [
        CaregiverLinkOut(
            link_id=str(l.id),
            caregiver_id=l.caregiver_id,
            patient_id=l.patient_id,
            status=l.status.value,
            visible_categories=l.visible_categories,
            relationship=l.relationship.value,
        )
        for l in links
    ]


@router.get("/{patient_id}/dashboard")
async def caregiver_patient_dashboard(
    patient_id: str,
    caregiver_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    consent_manager: Annotated[ConsentManager, Depends(get_consent_manager)],
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    """
    Read the patient's vital and medication summary as a caregiver.
    Consent is verified against the approved caregiver link — the caregiver
    can only see categories that were explicitly granted by the patient.
    """
    svc = CaregiverService(db=db, audit_logger=audit_logger, consent_manager=consent_manager)
    try:
        return await svc.get_patient_dashboard(
            caregiver_id=caregiver_id,
            patient_id=patient_id,
            fhir_timeline=fhir_timeline,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
