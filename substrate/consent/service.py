"""
platform/consent/service.py

ConsentManager — the single gatekeeping authority for all patient data access.

Every code path that reads or writes patient data MUST call check_consent()
before proceeding. There are no exceptions for "internal" services.

DPDP Act 2023 obligations implemented here:
- Grant: specific, informed, free, unambiguous consent with evidence
- Revoke: immediate; data principal can revoke at any time
- Check: purpose-bound + category-bound + entity-bound
- Expiry: automatic; expired consent is treated identically to revoked
- Sensitive categories (mental health, genetic): require explicit flags
- Caregiver delegation: the principal must actively grant it; not self-assigned
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from substrate.audit.models import AuditEvent, AuditEventType
from substrate.audit.service import AuditLogger
from substrate.consent.models import (
    CollectionMethod,
    ConsentGrant,
    ConsentRecord,
    ConsentRevocation,
    ConsentStatus,
    ConsentVerificationResult,
    DataCategory,
    ConsentPurpose,
    DelegationRelationship,
)
from substrate.consent.orm import ConsentRecordORM

logger = logging.getLogger(__name__)

# ── Purpose descriptions (plain language, shown to user before consent) ───────
# Production: load from a versioned, localised consent-text registry (en, hi, ta, etc.)
_PURPOSE_DESCRIPTIONS: dict[ConsentPurpose, str] = {
    ConsentPurpose.CLINICAL_DECISION_SUPPORT: (
        "Your de-identified health information will be used to assist a licensed clinician "
        "in making clinical decisions. No identifying information leaves your device or "
        "local hospital server."
    ),
    ConsentPurpose.EMERGENCY_CARE: (
        "In a detected emergency your care plan, allergy list, and critical health information "
        "will be shared with emergency services. This consent stays active until you revoke it."
    ),
    ConsentPurpose.CAREGIVER_MONITORING: (
        "Your designated caregiver will receive alerts about deviations in your health "
        "metrics, medication adherence, and vital-sign trends. You can revoke this at any time "
        "from the Privacy & Consent screen."
    ),
    ConsentPurpose.WELLNESS_TRACKING: (
        "Your lifestyle and health data will be analysed to generate personalised wellness "
        "insights. Data is stored locally and is never used to train AI models."
    ),
    ConsentPurpose.MEDICATION_ADHERENCE: (
        "Your medication schedule and dose log will be tracked to send you reminders and, "
        "if you have set up a caregiver, to alert them when doses are consistently missed."
    ),
    ConsentPurpose.CROSS_FACILITY_TRANSFER: (
        "Your health records will be shared with the receiving healthcare facility to support "
        "continuity of care. A copy of what is shared will remain visible in your consent log."
    ),
    ConsentPurpose.RESEARCH_ANONYMIZED: (
        "Fully anonymised (not linkable to you) health statistics will contribute to approved "
        "medical research. No data that could identify you is used."
    ),
}


class ConsentManager:
    """
    DPDP Act 2023 compliant consent management.

    Instantiate per-request with the active DB session and audit logger.
    """

    def __init__(self, db: AsyncSession, audit_logger: AuditLogger):
        self._db = db
        self._audit = audit_logger

    # ── Grant ─────────────────────────────────────────────────────────────────

    async def grant_consent(self, grant: ConsentGrant) -> ConsentRecord:
        """
        Record a new consent grant.

        Raises:
            SensitiveCategoryConsentError: if mental_health or genetic categories
                are requested without their explicit flags set.
        """
        self._validate_sensitive_categories(grant)

        purpose_description = _PURPOSE_DESCRIPTIONS.get(
            grant.purpose,
            grant.purpose.value,
        )

        record = ConsentRecord(
            data_principal_id=grant.data_principal_id,
            data_fiduciary_id=grant.data_fiduciary_id,
            data_fiduciary_name=grant.data_fiduciary_name,
            purpose=grant.purpose,
            purpose_description=purpose_description,
            data_categories=grant.data_categories,
            expires_at=grant.expires_at,
            delegated_to_id=grant.delegated_to_id,
            delegated_to_name=grant.delegated_to_name,
            delegation_relationship=grant.delegation_relationship,
            delegated_at=datetime.now(timezone.utc) if grant.delegated_to_id else None,
            collection_method=grant.collection_method,
            language=grant.language,
            consent_text_version=grant.consent_text_version,
            ip_address=grant.ip_address,
            user_agent=grant.user_agent,
            mental_health_explicit_consent=grant.mental_health_explicit_consent,
            genetic_data_explicit_consent=grant.genetic_data_explicit_consent,
        )

        orm = ConsentRecordORM.from_domain(record)
        self._db.add(orm)
        await self._db.flush()   # get DB-assigned ID before audit log

        entry_id = await self._audit.log(AuditEvent(
            event_type=AuditEventType.CONSENT_GRANTED,
            actor_id=grant.data_principal_id,
            resource_type="consent",
            resource_id=record.consent_id,
            details={
                "purpose": grant.purpose.value,
                "data_categories": [c.value for c in grant.data_categories],
                "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
                "delegated_to_id": grant.delegated_to_id,
                "consent_text_version": grant.consent_text_version,
                "language": grant.language,
            },
            ip_address=grant.ip_address,
        ))

        orm.audit_chain_entry_id = entry_id
        await self._db.commit()
        record.audit_chain_entry_id = entry_id

        logger.info(
            "consent_granted consent_id=%s principal=%s purpose=%s",
            record.consent_id, grant.data_principal_id, grant.purpose.value,
        )
        return record

    # ── Revoke ────────────────────────────────────────────────────────────────

    async def revoke_consent(
        self,
        revocation: ConsentRevocation,
        ip_address: str,
    ) -> ConsentRecord:
        """
        Revoke a consent grant. Takes effect immediately.

        Raises:
            ConsentNotFoundError: if the consent does not exist or is already inactive.
            ConsentAccessDeniedError: if the revoking entity is not the principal or delegate.
        """
        orm = await self._get_active_orm(revocation.consent_id)

        # Only the data principal (or their authorised delegate) may revoke.
        if (
            orm.data_principal_id != revocation.revoked_by_id
            and orm.delegated_to_id != revocation.revoked_by_id
        ):
            raise ConsentAccessDeniedError(
                f"Entity {revocation.revoked_by_id!r} is not authorised to revoke "
                f"consent {revocation.consent_id!r}."
            )

        now = datetime.now(timezone.utc)
        orm.status = ConsentStatus.REVOKED.value
        orm.revoked_at = now
        orm.revocation_reason = revocation.reason

        await self._audit.log(AuditEvent(
            event_type=AuditEventType.CONSENT_REVOKED,
            actor_id=revocation.revoked_by_id,
            resource_type="consent",
            resource_id=revocation.consent_id,
            details={"reason": revocation.reason},
            ip_address=ip_address,
        ))

        await self._db.commit()
        logger.info(
            "consent_revoked consent_id=%s revoked_by=%s",
            revocation.consent_id, revocation.revoked_by_id,
        )
        return orm.to_domain()

    # ── Check (the most important method — called on every data access) ───────

    async def check_consent(
        self,
        data_principal_id: str,
        requesting_entity_id: str,
        purpose: ConsentPurpose,
        data_categories: List[DataCategory],
    ) -> ConsentVerificationResult:
        """
        Verify that an active, non-expired consent exists that covers:
          - the data principal
          - the requesting entity (fiduciary or authorised delegate)
          - the stated purpose
          - all of the requested data categories (subset check)

        This MUST be called and the result checked (permitted == True) before
        any patient data is read, written, or transmitted.
        """
        now = datetime.now(timezone.utc)
        requested_set = {c.value for c in data_categories}

        result = await self._db.execute(
            select(ConsentRecordORM).where(
                and_(
                    ConsentRecordORM.data_principal_id == data_principal_id,
                    ConsentRecordORM.purpose == purpose.value,
                    ConsentRecordORM.status == ConsentStatus.ACTIVE.value,
                )
            )
        )
        records = result.scalars().all()

        for orm in records:
            # Auto-expire stale records in-band (lazy expiry).
            if orm.expires_at and orm.expires_at < now:
                await self._expire(orm)
                continue

            # Category coverage: every requested category must be in the consent.
            consented_set = set(orm.data_categories)
            if not requested_set.issubset(consented_set):
                continue

            # Entity check: requesting entity must be the fiduciary or its delegate.
            if (
                orm.data_fiduciary_id != requesting_entity_id
                and orm.delegated_to_id != requesting_entity_id
            ):
                continue

            await self._audit.log(AuditEvent(
                event_type=AuditEventType.CONSENT_CHECKED_PERMITTED,
                actor_id=requesting_entity_id,
                resource_type="consent",
                resource_id=orm.consent_id,
                details={"purpose": purpose.value, "categories": list(requested_set)},
                ip_address="internal",
            ))
            return ConsentVerificationResult(
                permitted=True,
                consent_id=orm.consent_id,
                expires_at=orm.expires_at,
            )

        await self._audit.log(AuditEvent(
            event_type=AuditEventType.CONSENT_CHECKED_DENIED,
            actor_id=requesting_entity_id,
            resource_type="consent",
            resource_id=None,
            details={
                "principal": data_principal_id,
                "purpose": purpose.value,
                "categories": list(requested_set),
            },
            ip_address="internal",
        ))
        return ConsentVerificationResult(
            permitted=False,
            denial_reason=(
                f"No active consent found for principal={data_principal_id!r}, "
                f"purpose={purpose.value!r}, categories={sorted(requested_set)}"
            ),
        )

    # ── Helper: list a principal's consents (for the consent dashboard UI) ───

    async def list_consents(self, data_principal_id: str) -> List[ConsentRecord]:
        result = await self._db.execute(
            select(ConsentRecordORM).where(
                ConsentRecordORM.data_principal_id == data_principal_id
            )
        )
        return [orm.to_domain() for orm in result.scalars().all()]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _validate_sensitive_categories(self, grant: ConsentGrant) -> None:
        if DataCategory.MENTAL_HEALTH in grant.data_categories:
            if not grant.mental_health_explicit_consent:
                raise SensitiveCategoryConsentError(
                    "Mental health data requires mental_health_explicit_consent=True "
                    "to confirm the user has seen the additional disclosure."
                )
        if DataCategory.GENETIC in grant.data_categories:
            if not grant.genetic_data_explicit_consent:
                raise SensitiveCategoryConsentError(
                    "Genetic data requires genetic_data_explicit_consent=True."
                )

    async def _get_active_orm(self, consent_id: str) -> ConsentRecordORM:
        result = await self._db.execute(
            select(ConsentRecordORM).where(
                and_(
                    ConsentRecordORM.consent_id == consent_id,
                    ConsentRecordORM.status == ConsentStatus.ACTIVE.value,
                )
            )
        )
        orm = result.scalar_one_or_none()
        if not orm:
            raise ConsentNotFoundError(consent_id)
        return orm

    async def _expire(self, orm: ConsentRecordORM) -> None:
        orm.status = ConsentStatus.EXPIRED.value
        await self._db.commit()
        logger.debug("consent_expired consent_id=%s", orm.consent_id)


# ── Exceptions ────────────────────────────────────────────────────────────────

class ConsentNotFoundError(Exception):
    pass

class ConsentAccessDeniedError(Exception):
    pass

class SensitiveCategoryConsentError(Exception):
    pass
