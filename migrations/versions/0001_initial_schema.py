"""Initial platform schema

Revision ID: 0001
Revises:
Create Date: 2026-07-01 00:00:00.000000

This migration creates the initial schema from infrastructure/postgres/init.sql.
In a fresh docker-compose environment, init.sql runs automatically.
This migration is the equivalent for Alembic-managed environments (staging, prod).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── consent_records ────────────────────────────────────────────────────
    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("data_principal_id", sa.Text, nullable=False),
        sa.Column("requesting_entity_id", sa.Text, nullable=False),
        sa.Column("purpose", sa.Text, nullable=False),
        sa.Column("data_categories", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="ACTIVE"),
        sa.Column("collection_method", sa.Text, nullable=False),
        sa.Column("is_sensitive_category", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sensitive_category_explicit_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_delegated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("delegate_id", sa.Text),
        sa.Column("delegation_relationship", sa.Text),
        sa.Column("delegation_granted_by", sa.Text),
        sa.Column("granted_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("revocation_reason", sa.Text),
        sa.Column("ip_address", sa.Text),
        sa.Column("evidence_hash", sa.Text),
        sa.Column("audit_chain_entry_id", sa.Text),
        sa.Column("consent_text_version", sa.Text, nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_consent_principal", "consent_records", ["data_principal_id"])
    op.create_index("idx_consent_status", "consent_records", ["status"])
    op.create_index("idx_consent_purpose", "consent_records", ["purpose"])

    # ── clinicore_patients ─────────────────────────────────────────────────
    op.create_table(
        "clinicore_patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("keycloak_user_id", sa.Text, unique=True, nullable=False),
        sa.Column("abha_id", sa.Text, unique=True),
        sa.Column("full_name_enc", sa.LargeBinary, nullable=False),
        sa.Column("dob_enc", sa.LargeBinary, nullable=False),
        sa.Column("phone_enc", sa.LargeBinary),
        sa.Column("email_enc", sa.LargeBinary),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── clinicore_consultations ────────────────────────────────────────────
    op.create_table(
        "clinicore_consultations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinicore_patients.id"), nullable=False),
        sa.Column("clinician_id", sa.Text, nullable=False),
        sa.Column("facility_id", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="ACTIVE"),
        sa.Column("chief_complaint", sa.Text),
        sa.Column("consent_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consent_records.id")),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_clinicore_consult_patient", "clinicore_consultations", ["patient_id"])
    op.create_index("idx_clinicore_consult_clinician", "clinicore_consultations", ["clinician_id"])

    # ── clinicore_messages ─────────────────────────────────────────────────
    op.create_table(
        "clinicore_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("consultation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinicore_consultations.id"), nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("content_enc", sa.LargeBinary, nullable=False),
        sa.Column("model_used", sa.Text),
        sa.Column("routed_to", sa.Text),
        sa.Column("phi_risk_score", sa.Float),
        sa.Column("grounding_score", sa.Float),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_clinicore_msg_consult", "clinicore_messages", ["consultation_id"])

    # ── relaymed_patients ──────────────────────────────────────────────────
    op.create_table(
        "relaymed_patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("keycloak_user_id", sa.Text, unique=True, nullable=False),
        sa.Column("abha_id", sa.Text, unique=True),
        sa.Column("full_name_enc", sa.LargeBinary, nullable=False),
        sa.Column("dob_enc", sa.LargeBinary, nullable=False),
        sa.Column("phone_enc", sa.LargeBinary),
        sa.Column("email_enc", sa.LargeBinary),
        sa.Column("chronic_conditions", postgresql.ARRAY(sa.Text)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── relaymed_caregiver_links ───────────────────────────────────────────
    op.create_table(
        "relaymed_caregiver_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("caregiver_id", sa.Text, nullable=False),
        sa.Column("patient_id", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="PENDING"),
        sa.Column("relationship", sa.Text, nullable=False),
        sa.Column("visible_categories", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("consent_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consent_records.id")),
        sa.Column("requested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("resolved_by", sa.Text),
        sa.UniqueConstraint("caregiver_id", "patient_id", name="uq_caregiver_patient"),
    )

    # ── relaymed_medication_schedules ──────────────────────────────────────
    op.create_table(
        "relaymed_medication_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", sa.Text, nullable=False),
        sa.Column("medication_name", sa.Text, nullable=False),
        sa.Column("dose", sa.Text, nullable=False),
        sa.Column("frequency", sa.Text, nullable=False),
        sa.Column("times", postgresql.ARRAY(sa.Text)),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("fhir_resource_id", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── secops_events ──────────────────────────────────────────────────────
    op.create_table(
        "secops_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("actor_id", sa.Text),
        sa.Column("source_ip", sa.Text),
        sa.Column("severity", sa.Text, nullable=False, server_default="INFO"),
        sa.Column("raw", postgresql.JSONB),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("secops_events")
    op.drop_table("relaymed_medication_schedules")
    op.drop_table("relaymed_caregiver_links")
    op.drop_table("relaymed_patients")
    op.drop_table("clinicore_messages")
    op.drop_table("clinicore_consultations")
    op.drop_table("clinicore_patients")
    op.drop_table("consent_records")
