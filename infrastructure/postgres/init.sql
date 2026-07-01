-- infrastructure/postgres/init.sql
--
-- Initial database schema for the Clinicore platform.
-- Tables are namespaced by prefix so the single Postgres instance serves
-- both Clinicore (B2B) and RelayMed (B2C) without cross-database joins.
--
-- Production: managed by Alembic migrations in infrastructure/ci/.
-- This init.sql is ONLY for the docker-compose dev environment first-boot.
-- It is idempotent (CREATE TABLE IF NOT EXISTS throughout).

-- Enable pgcrypto for column-level encryption helpers and uuid generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── consent_ tables ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS consent_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_principal_id   TEXT NOT NULL,
    requesting_entity_id TEXT NOT NULL,
    purpose         TEXT NOT NULL,
    data_categories TEXT[] NOT NULL,
    status          TEXT NOT NULL DEFAULT 'ACTIVE',
    collection_method TEXT NOT NULL,
    is_sensitive_category BOOLEAN NOT NULL DEFAULT FALSE,
    sensitive_category_explicit_flag BOOLEAN NOT NULL DEFAULT FALSE,
    is_delegated    BOOLEAN NOT NULL DEFAULT FALSE,
    delegate_id     TEXT,
    delegation_relationship TEXT,
    delegation_granted_by TEXT,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    revocation_reason TEXT,
    ip_address      TEXT,
    evidence_hash   TEXT,
    audit_chain_entry_id TEXT,
    consent_text_version TEXT NOT NULL DEFAULT '1.0',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consent_principal ON consent_records (data_principal_id);
CREATE INDEX IF NOT EXISTS idx_consent_status ON consent_records (status);
CREATE INDEX IF NOT EXISTS idx_consent_purpose ON consent_records (purpose);
CREATE INDEX IF NOT EXISTS idx_consent_expires ON consent_records (expires_at) WHERE expires_at IS NOT NULL;

-- ── clinicore_ tables ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS clinicore_patients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keycloak_user_id TEXT UNIQUE NOT NULL,
    abha_id         TEXT UNIQUE,
    full_name_enc   BYTEA NOT NULL,   -- AES-256-GCM via Vault Transit
    dob_enc         BYTEA NOT NULL,
    phone_enc       BYTEA,
    email_enc       BYTEA,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clinicore_consultations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES clinicore_patients(id),
    clinician_id    TEXT NOT NULL,   -- Keycloak user ID of the clinician
    facility_id     TEXT,
    status          TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE | CLOSED | ESCALATED
    chief_complaint TEXT,
    consent_record_id UUID REFERENCES consent_records(id),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    message_count   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clinicore_consult_patient ON clinicore_consultations(patient_id);
CREATE INDEX IF NOT EXISTS idx_clinicore_consult_clinician ON clinicore_consultations(clinician_id);
CREATE INDEX IF NOT EXISTS idx_clinicore_consult_status ON clinicore_consultations(status);

CREATE TABLE IF NOT EXISTS clinicore_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID NOT NULL REFERENCES clinicore_consultations(id),
    role            TEXT NOT NULL,   -- user | assistant | system
    content_enc     BYTEA NOT NULL,   -- AES-256-GCM encrypted
    model_used      TEXT,
    routed_to       TEXT,   -- cloud | onprem
    phi_risk_score  FLOAT,
    grounding_score FLOAT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clinicore_msg_consult ON clinicore_messages(consultation_id);

-- ── relaymed_ tables ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS relaymed_patients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keycloak_user_id TEXT UNIQUE NOT NULL,
    abha_id         TEXT UNIQUE,
    full_name_enc   BYTEA NOT NULL,
    dob_enc         BYTEA NOT NULL,
    phone_enc       BYTEA,
    email_enc       BYTEA,
    chronic_conditions TEXT[],   -- e.g. ['T2DM', 'hypertension'] — not PHI, just ICD codes
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS relaymed_caregiver_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    caregiver_id    TEXT NOT NULL,   -- Keycloak user ID of caregiver
    patient_id      TEXT NOT NULL,   -- Keycloak user ID of patient (data principal)
    status          TEXT NOT NULL DEFAULT 'PENDING',   -- PENDING | APPROVED | DECLINED | REVOKED
    relationship    TEXT NOT NULL,   -- e.g. CHILD_TO_PARENT
    visible_categories TEXT[] NOT NULL,
    consent_record_id UUID REFERENCES consent_records(id),
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT,   -- patient's Keycloak ID who approved/declined
    UNIQUE (caregiver_id, patient_id)
);

CREATE INDEX IF NOT EXISTS idx_caregiver_links_caregiver ON relaymed_caregiver_links(caregiver_id);
CREATE INDEX IF NOT EXISTS idx_caregiver_links_patient ON relaymed_caregiver_links(patient_id);
CREATE INDEX IF NOT EXISTS idx_caregiver_links_status ON relaymed_caregiver_links(status);

CREATE TABLE IF NOT EXISTS relaymed_medication_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      TEXT NOT NULL,
    medication_name TEXT NOT NULL,
    dose            TEXT NOT NULL,
    frequency       TEXT NOT NULL,   -- e.g. "twice_daily", "once_weekly"
    times           TEXT[],          -- e.g. ['08:00', '20:00']
    start_date      DATE NOT NULL,
    end_date        DATE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    fhir_resource_id TEXT,           -- reference back to FHIR MedicationStatement
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_med_schedule_patient ON relaymed_medication_schedules(patient_id);

-- ── secops_ tables (UEBA / detection event log) ───────────────────────────

CREATE TABLE IF NOT EXISTS secops_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      TEXT NOT NULL,
    actor_id        TEXT,
    source_ip       TEXT,
    severity        TEXT NOT NULL DEFAULT 'INFO',
    raw             JSONB,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_secops_events_type ON secops_events(event_type);
CREATE INDEX IF NOT EXISTS idx_secops_events_actor ON secops_events(actor_id);
CREATE INDEX IF NOT EXISTS idx_secops_events_processed ON secops_events(processed_at);
