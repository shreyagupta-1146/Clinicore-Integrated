"""
platform/consent/orm.py

SQLAlchemy 2.0 async-mapped ORM for the consent ledger.

This table is intentionally append-heavy and rarely deletes rows: a revoked
or expired consent stays in the table (status changes) so the consent
*history* itself is auditable. Actual deletion only happens via the DPDP
"right to erasure" workflow, which is a separate, logged operation
(not implemented in this MVP — see ai_services/eval_harness/ROADMAP notes
in the README for Phase 2 scope).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import ARRAY, Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from substrate.consent.models import (
    CollectionMethod,
    ConsentRecord,
    ConsentStatus,
    DataCategory,
    ConsentPurpose,
    DelegationRelationship,
)
from substrate.db.base import Base


class ConsentRecordORM(Base):
    __tablename__ = "consent_records"
    __table_args__ = (
        Index("ix_consent_principal_purpose_status", "data_principal_id", "purpose", "status"),
        Index("ix_consent_delegated_to", "delegated_to_id"),
    )

    # Internal surrogate PK (DB identity); consent_id is the stable public/business key.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    consent_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)

    data_principal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    data_principal_abha_id: Mapped[Optional[str]] = mapped_column(String(14), nullable=True)

    data_fiduciary_id: Mapped[str] = mapped_column(String(128), nullable=False)
    data_fiduciary_name: Mapped[str] = mapped_column(String(256), nullable=False)

    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose_description: Mapped[str] = mapped_column(Text, nullable=False)

    data_categories: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)

    delegated_to_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    delegated_to_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    delegation_relationship: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    delegated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ConsentStatus.ACTIVE.value)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    collection_method: Mapped[str] = mapped_column(String(32), nullable=False, default=CollectionMethod.APP_UI.value)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    consent_text_version: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=False)

    fhir_consent_resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    abdm_consent_artefact_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    audit_chain_entry_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    mental_health_explicit_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    genetic_data_explicit_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    @classmethod
    def from_domain(cls, record: ConsentRecord) -> "ConsentRecordORM":
        return cls(
            consent_id=record.consent_id,
            data_principal_id=record.data_principal_id,
            data_principal_abha_id=record.data_principal_abha_id,
            data_fiduciary_id=record.data_fiduciary_id,
            data_fiduciary_name=record.data_fiduciary_name,
            purpose=record.purpose.value,
            purpose_description=record.purpose_description,
            data_categories=[c.value for c in record.data_categories],
            delegated_to_id=record.delegated_to_id,
            delegated_to_name=record.delegated_to_name,
            delegation_relationship=(
                record.delegation_relationship.value if record.delegation_relationship else None
            ),
            delegated_at=record.delegated_at,
            granted_at=record.granted_at,
            expires_at=record.expires_at,
            status=record.status.value,
            revoked_at=record.revoked_at,
            revocation_reason=record.revocation_reason,
            collection_method=record.collection_method.value,
            language=record.language,
            consent_text_version=record.consent_text_version,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
            fhir_consent_resource_id=record.fhir_consent_resource_id,
            abdm_consent_artefact_id=record.abdm_consent_artefact_id,
            audit_chain_entry_id=record.audit_chain_entry_id,
            mental_health_explicit_consent=record.mental_health_explicit_consent,
            genetic_data_explicit_consent=record.genetic_data_explicit_consent,
        )

    def to_domain(self) -> ConsentRecord:
        return ConsentRecord(
            consent_id=self.consent_id,
            data_principal_id=self.data_principal_id,
            data_principal_abha_id=self.data_principal_abha_id,
            data_fiduciary_id=self.data_fiduciary_id,
            data_fiduciary_name=self.data_fiduciary_name,
            purpose=ConsentPurpose(self.purpose),
            purpose_description=self.purpose_description,
            data_categories=[DataCategory(c) for c in self.data_categories],
            delegated_to_id=self.delegated_to_id,
            delegated_to_name=self.delegated_to_name,
            delegation_relationship=(
                DelegationRelationship(self.delegation_relationship)
                if self.delegation_relationship else None
            ),
            delegated_at=self.delegated_at,
            granted_at=self.granted_at,
            expires_at=self.expires_at,
            status=ConsentStatus(self.status),
            revoked_at=self.revoked_at,
            revocation_reason=self.revocation_reason,
            collection_method=CollectionMethod(self.collection_method),
            language=self.language,
            consent_text_version=self.consent_text_version,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            fhir_consent_resource_id=self.fhir_consent_resource_id,
            abdm_consent_artefact_id=self.abdm_consent_artefact_id,
            audit_chain_entry_id=self.audit_chain_entry_id,
            mental_health_explicit_consent=self.mental_health_explicit_consent,
            genetic_data_explicit_consent=self.genetic_data_explicit_consent,
        )
