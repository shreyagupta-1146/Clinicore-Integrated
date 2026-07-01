"""
apps/relaymed/backend/modules/caregiver/service.py

Caregiver delegation workflow: request -> patient approval -> consent grant.

This is the concrete implementation of the integration plan's caregiver
requirement: a child can ask to monitor a parent, but the parent (data
principal) must actively approve — approval is what creates the actual
DPDP consent grant via ConsentManager. Declining or never responding means
no access, full stop; there is no default-allow path.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.relaymed.backend.models.caregiver import CaregiverLinkORM, CaregiverLinkStatus
from substrate.audit.models import AuditEvent, AuditEventType
from substrate.audit.service import AuditLogger
from substrate.consent.models import (
    ConsentGrant,
    ConsentPurpose,
    ConsentRevocation,
    DataCategory,
    DelegationRelationship,
)
from substrate.consent.service import ConsentManager


_VISIBLE_CATEGORY_MAP = {
    "vitals": DataCategory.VITALS,
    "medications": DataCategory.MEDICATIONS,
    "lifestyle": DataCategory.LIFESTYLE,
    "conditions": DataCategory.CONDITIONS,
    "care_plan": DataCategory.CARE_PLAN,
}


class CaregiverLinkNotFoundError(Exception):
    pass


class CaregiverService:
    def __init__(self, db: AsyncSession, consent_manager: ConsentManager, audit_logger: AuditLogger):
        self._db = db
        self._consent = consent_manager
        self._audit = audit_logger

    async def request_link(
        self,
        *,
        patient_id: str,
        caregiver_id: str,
        caregiver_display_name: str,
        relationship: DelegationRelationship,
        requested_categories: List[str],
        ip_address: str,
    ) -> CaregiverLinkORM:
        invalid = [c for c in requested_categories if c not in _VISIBLE_CATEGORY_MAP]
        if invalid:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown data categories: {invalid}")

        link = CaregiverLinkORM(
            patient_id=patient_id,
            caregiver_id=caregiver_id,
            caregiver_display_name=caregiver_display_name,
            relationship=relationship.value,
            status=CaregiverLinkStatus.PENDING.value,
            visible_categories=",".join(requested_categories),
        )
        self._db.add(link)
        await self._db.commit()

        await self._audit.log(AuditEvent(
            event_type=AuditEventType.WELLNESS_CAREGIVER_ASSIGNED,
            actor_id=caregiver_id,
            resource_type="caregiver_link",
            resource_id=link.link_id,
            details={"patient_id": patient_id, "status": "requested"},
            ip_address=ip_address,
        ))
        return link

    async def approve_link(
        self, *, link_id: str, patient_id: str, consent_text_version: str, ip_address: str, user_agent: str
    ) -> CaregiverLinkORM:
        link = await self._get_link(link_id)
        if link.patient_id != patient_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the patient may approve this link")
        if link.status != CaregiverLinkStatus.PENDING.value:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Link is not pending (status={link.status})")

        categories = [_VISIBLE_CATEGORY_MAP[c] for c in link.visible_categories.split(",") if c]

        grant = ConsentGrant(
            data_principal_id=patient_id,
            data_fiduciary_id="relaymed",
            data_fiduciary_name="RelayMed",
            purpose=ConsentPurpose.CAREGIVER_MONITORING,
            data_categories=categories,
            delegated_to_id=link.caregiver_id,
            delegated_to_name=link.caregiver_display_name,
            delegation_relationship=DelegationRelationship(link.relationship),
            consent_text_version=consent_text_version,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        consent_record = await self._consent.grant_consent(grant)

        from datetime import datetime, timezone
        link.status = CaregiverLinkStatus.ACTIVE.value
        link.decided_at = datetime.now(timezone.utc)
        link.consent_id = consent_record.consent_id
        await self._db.commit()
        return link

    async def decline_link(self, *, link_id: str, patient_id: str) -> CaregiverLinkORM:
        link = await self._get_link(link_id)
        if link.patient_id != patient_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the patient may decline this link")

        from datetime import datetime, timezone
        link.status = CaregiverLinkStatus.DECLINED.value
        link.decided_at = datetime.now(timezone.utc)
        await self._db.commit()
        return link

    async def revoke_link(self, *, link_id: str, patient_id: str, ip_address: str) -> CaregiverLinkORM:
        link = await self._get_link(link_id)
        if link.patient_id != patient_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the patient may revoke this link")
        if link.status != CaregiverLinkStatus.ACTIVE.value:
            raise HTTPException(status.HTTP_409_CONFLICT, "Link is not active")

        if link.consent_id:
            await self._consent.revoke_consent(
                ConsentRevocation(
                    consent_id=link.consent_id,
                    revoked_by_id=patient_id,
                    reason="Caregiver link revoked by patient.",
                ),
                ip_address=ip_address,
            )

        link.status = CaregiverLinkStatus.REVOKED.value
        await self._db.commit()

        await self._audit.log(AuditEvent(
            event_type=AuditEventType.WELLNESS_CAREGIVER_REMOVED,
            actor_id=patient_id,
            resource_type="caregiver_link",
            resource_id=link.link_id,
            details={"caregiver_id": link.caregiver_id},
            ip_address=ip_address,
        ))
        return link

    async def list_links_for_patient(self, patient_id: str) -> List[CaregiverLinkORM]:
        result = await self._db.execute(
            select(CaregiverLinkORM).where(CaregiverLinkORM.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def list_active_links_for_caregiver(self, caregiver_id: str) -> List[CaregiverLinkORM]:
        result = await self._db.execute(
            select(CaregiverLinkORM).where(
                and_(
                    CaregiverLinkORM.caregiver_id == caregiver_id,
                    CaregiverLinkORM.status == CaregiverLinkStatus.ACTIVE.value,
                )
            )
        )
        return list(result.scalars().all())

    async def _get_link(self, link_id: str) -> CaregiverLinkORM:
        result = await self._db.execute(
            select(CaregiverLinkORM).where(CaregiverLinkORM.link_id == link_id)
        )
        link = result.scalar_one_or_none()
        if link is None:
            raise CaregiverLinkNotFoundError(link_id)
        return link
