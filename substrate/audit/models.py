"""
platform/audit/models.py

Audit event types and entry schema.

Every action that touches patient data, consent, or security state
must produce an AuditEvent. The AuditLogger writes it to the
hash-chained immudb store. No direct DB writes from app code.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    # ── Consent ──────────────────────────────────────────────────────────────
    CONSENT_GRANTED = "consent.granted"
    CONSENT_REVOKED = "consent.revoked"
    CONSENT_EXPIRED = "consent.expired"
    CONSENT_CHECKED_PERMITTED = "consent.check.permitted"
    CONSENT_CHECKED_DENIED = "consent.check.denied"

    # ── Authentication ───────────────────────────────────────────────────────
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_MFA_CHALLENGE = "auth.mfa.challenge"
    AUTH_MFA_SUCCESS = "auth.mfa.success"
    AUTH_MFA_FAILURE = "auth.mfa.failure"
    AUTH_STEP_UP = "auth.step_up"
    AUTH_BREAK_GLASS = "auth.break_glass"
    AUTH_ACCOUNT_LOCKED = "auth.account.locked"
    AUTH_PASSWORD_RESET = "auth.password.reset"

    # ── Clinical (Clinicore) ─────────────────────────────────────────────────
    CLINICAL_CHAT_CREATED = "clinical.chat.created"
    CLINICAL_CHAT_ACCESSED = "clinical.chat.accessed"
    CLINICAL_MESSAGE_SENT = "clinical.message.sent"
    CLINICAL_AI_RESPONSE = "clinical.ai.response"
    CLINICAL_FOLDER_SHARED = "clinical.folder.shared"
    CLINICAL_SHARE_ACCEPTED = "clinical.share.accepted"
    CLINICAL_SHARE_REVOKED = "clinical.share.revoked"
    CLINICAL_STEPUP_UNLOCKED = "clinical.stepup.folder.unlocked"
    CLINICAL_CONTINUATION_CREATED = "clinical.continuation.created"
    CLINICAL_RESEARCH_SEARCHED = "clinical.research.searched"

    # ── Wellness / RelayMed ──────────────────────────────────────────────────
    WELLNESS_VITAL_INGESTED = "wellness.vital.ingested"
    WELLNESS_ANOMALY_DETECTED = "wellness.anomaly.detected"
    WELLNESS_ALERT_SENT = "wellness.alert.sent"
    WELLNESS_CAREGIVER_ASSIGNED = "wellness.caregiver.assigned"
    WELLNESS_CAREGIVER_REMOVED = "wellness.caregiver.removed"
    WELLNESS_REPORT_GENERATED = "wellness.report.generated"
    WELLNESS_MEDICATION_LOGGED = "wellness.medication.logged"
    WELLNESS_DOSE_MISSED = "wellness.dose.missed"
    WELLNESS_DOSE_REMINDER_SENT = "wellness.dose.reminder.sent"
    WELLNESS_CARE_PLAN_UPDATED = "wellness.care_plan.updated"

    # ── PHI vault / de-identification ────────────────────────────────────────
    PHI_ACCESSED = "phi.accessed"
    PHI_EXPORTED = "phi.exported"
    PHI_DEIDENTIFIED = "phi.deidentified"
    PHI_REIDENTIFICATION_RISK = "phi.reidentification_risk.flagged"

    # ── Security (SecOps) ────────────────────────────────────────────────────
    SECOPS_THREAT_DETECTED = "secops.threat.detected"
    SECOPS_RESPONSE_TRIGGERED = "secops.response.triggered"
    SECOPS_HUMAN_AUTH_REQUESTED = "secops.human_auth.requested"
    SECOPS_HUMAN_AUTH_GRANTED = "secops.human_auth.granted"
    SECOPS_HUMAN_AUTH_DENIED = "secops.human_auth.denied"
    SECOPS_HUMAN_AUTH_TIMEOUT = "secops.human_auth.timeout"
    SECOPS_IP_BLOCKED = "secops.ip.blocked"
    SECOPS_ACCOUNT_RESTRICTED = "secops.account.restricted"

    # ── Admin ────────────────────────────────────────────────────────────────
    ADMIN_USER_CREATED = "admin.user.created"
    ADMIN_ROLE_CHANGED = "admin.role.changed"
    ADMIN_SETTINGS_CHANGED = "admin.settings.changed"
    ADMIN_DATA_EXPORT = "admin.data.export"
    ADMIN_DATA_DELETION = "admin.data.deletion"


class AuditEvent(BaseModel):
    """
    The input to the audit logger. All fields are required except resource_id.
    The audit logger wraps this in an AuditEntry before chain-appending.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType
    actor_id: str           # User ID of who performed the action
    actor_role: Optional[str] = None
    resource_type: str      # "consent", "chat", "folder", "vital", etc.
    resource_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: str
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    # Set by the service if an existing consent was used to authorise access
    authorising_consent_id: Optional[str] = None


class AuditEntry(BaseModel):
    """
    The record actually written to the chain.
    Includes the chain linkage fields (prev_hash, entry_hash).
    """
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event: AuditEvent
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prev_hash: str          # Hash of the previous entry (or genesis hash for entry 0)
    entry_hash: Optional[str] = None   # Set after hashing; None until computed
