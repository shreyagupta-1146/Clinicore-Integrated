"""
apps/relaymed/backend/models/medication.py

Medication schedule + dose log. The MedicationStatement itself (drug, dose,
prescriber) is mirrored to the shared FHIR timeline so Clinicore can see it;
this table holds the RelayMed-specific *schedule and adherence log* (times
of day, reminders sent, doses taken/missed) that has no FHIR equivalent
worth modelling for the MVP.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from substrate.db.base import Base


class MedicationScheduleORM(Base):
    __tablename__ = "relaymed_medication_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))

    patient_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    drug_name: Mapped[str] = mapped_column(String(256), nullable=False)
    dose_description: Mapped[str] = mapped_column(String(128), nullable=False)  # "500mg", "1 tablet" — display only
    fhir_medication_statement_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class DoseLogORM(Base):
    __tablename__ = "relaymed_dose_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dose_log_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))

    schedule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("relaymed_medication_schedules.schedule_id"), nullable=False, index=True
    )
    patient_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    taken_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending|taken|missed
