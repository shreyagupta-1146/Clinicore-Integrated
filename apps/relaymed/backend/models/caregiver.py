"""
apps/relaymed/backend/models/caregiver.py

Caregiver delegation — the new loop the integration plan requires RelayMed
to support: adult children monitoring an elderly parent's chronic-condition
vitals and medication adherence.

DPDP-correctness invariant (this is the whole point of this table):
A CaregiverLinkORM row only becomes "active" after the PRINCIPAL (the
patient/parent) approves it. A caregiver can REQUEST a link; they cannot
grant themselves access. Approval triggers a real consent grant via
ConsentManager (purpose=CAREGIVER_MONITORING, delegated_to_id=caregiver_id) —
this table tracks the relationship/UX state, the substrate consent ledger
is what's actually checked on every data read.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from substrate.db.base import Base


class CaregiverLinkStatus(str, Enum):
    PENDING = "pending"           # Caregiver requested; awaiting patient approval
    ACTIVE = "active"             # Patient approved; consent granted
    DECLINED = "declined"         # Patient declined the request
    REVOKED = "revoked"           # Patient revoked a previously-active link


class CaregiverLinkORM(Base):
    __tablename__ = "relaymed_caregiver_links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    link_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))

    patient_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    caregiver_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    caregiver_display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    relationship: Mapped[str] = mapped_column(String(32), nullable=False)  # DelegationRelationship value

    status: Mapped[str] = mapped_column(String(16), default=CaregiverLinkStatus.PENDING.value)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Linkage to the substrate consent record created on approval
    consent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # What the caregiver is allowed to see — subset of DataCategory values.
    # Patient chooses this at approval time (e.g., vitals + adherence, NOT mental_health).
    visible_categories: Mapped[str] = mapped_column(String(512), nullable=False, default="vitals,medications")

    alert_on_missed_dose: Mapped[bool] = mapped_column(default=True)
    alert_on_vital_anomaly: Mapped[bool] = mapped_column(default=True)
