"""
apps/clinicore/backend/models/patient.py

Minimal patient record scoped to a clinic. This is NOT the source of truth
for clinical data — that lives in the shared FHIR timeline
(substrate/fhir/timeline.py), keyed by the same patient_id (and, where
linked, the patient's ABHA ID). This table exists so Clinicore can list
"my clinic's patients" and FK consultations to a clinic-scoped patient row
without duplicating clinical data into Clinicore's own database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from substrate.db.base import Base


class ClinicPatientORM(Base):
    __tablename__ = "clinicore_clinic_patients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))

    clinic_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    abha_id: Mapped[Optional[str]] = mapped_column(String(14), nullable=True, index=True)

    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    registered_by_clinician_id: Mapped[str] = mapped_column(String(128), nullable=False)
