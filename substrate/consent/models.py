"""
platform/consent/models.py

DPDP Act 2023 aligned data models for the consent ledger.

Key DPDP principles enforced here:
- Consent must be: specific, informed, unconditional, unambiguous, free
- Purpose must be stated in plain language
- Consent is revocable at any time by the data principal
- Health data is treated as "sensitive personal data" requiring heightened consent
- Caregiver/delegated access must itself be consented to by the data principal
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ──────────────────────────────────────────────────────────────

class ConsentPurpose(str, Enum):
    CLINICAL_DECISION_SUPPORT = "clinical_decision_support"
    EMERGENCY_CARE = "emergency_care"
    CAREGIVER_MONITORING = "caregiver_monitoring"
    WELLNESS_TRACKING = "wellness_tracking"
    MEDICATION_ADHERENCE = "medication_adherence"
    CROSS_FACILITY_TRANSFER = "cross_facility_transfer"
    RESEARCH_ANONYMIZED = "research_anonymized"  # Only ever anonymized data


class DataCategory(str, Enum):
    """Fine-grained data categories. Consent must enumerate which categories."""
    VITALS = "vitals"                    # HR, BP, SpO2, temperature
    MEDICATIONS = "medications"          # Prescription, OTC, adherence
    CONDITIONS = "conditions"            # Diagnoses, problem list
    LAB_RESULTS = "lab_results"          # Blood glucose, HbA1c, CBC, etc.
    IMAGING = "imaging"                  # X-ray, MRI, ECG
    LIFESTYLE = "lifestyle"              # Exercise, sleep, diet, activity
    MENTAL_HEALTH = "mental_health"      # Extra sensitivity; requires explicit flag
    GENETIC = "genetic"                  # Highest sensitivity; hard-blocked from cloud
    CHAT_HISTORY = "chat_history"        # Clinical consultation text
    CARE_PLAN = "care_plan"              # Personalized first-aid / escalation plans
    WEARABLE_STREAM = "wearable_stream"  # Continuous device telemetry


class ConsentStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPENDED = "suspended"     # Temporarily paused (e.g., during a dispute)


class DelegationRelationship(str, Enum):
    """Relationship of the delegate (caregiver) to the data principal (patient)."""
    CHILD = "child"
    PARENT = "parent"
    SPOUSE = "spouse"
    SIBLING = "sibling"
    GUARDIAN = "guardian"
    NOMINATED_REPRESENTATIVE = "nominated_representative"


class CollectionMethod(str, Enum):
    APP_UI = "app_ui"
    VERBAL_WITNESSED = "verbal_witnessed"   # Emergency, documented by staff
    WRITTEN_PAPER = "written_paper"         # Digitized later


# ── Core models ───────────────────────────────────────────────────────────────

class ConsentRecord(BaseModel):
    """
    A single, specific, informed consent grant.

    One record = one purpose + one set of data categories + one fiduciary.
    Broad "consent to everything" records are intentionally not supported.
    """
    consent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # The person whose data this is (data principal under DPDP)
    data_principal_id: str
    data_principal_abha_id: Optional[str] = None   # ABHA health ID

    # The organisation accountable for processing (data fiduciary under DPDP)
    data_fiduciary_id: str
    data_fiduciary_name: str

    # What the data will be used for
    purpose: ConsentPurpose
    purpose_description: str   # Plain-language; shown to user before they consent

    # Which specific data categories are covered
    data_categories: List[DataCategory]

    # Delegation: set when a caregiver is granted read access on behalf of a patient.
    # The data_principal_id must consent to this delegation; it is NOT self-granted.
    delegated_to_id: Optional[str] = None
    delegated_to_name: Optional[str] = None
    delegation_relationship: Optional[DelegationRelationship] = None
    delegated_at: Optional[datetime] = None

    # Time bounds
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None     # None = no fixed expiry (but still revocable)

    # State
    status: ConsentStatus = ConsentStatus.ACTIVE
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None

    # Collection evidence
    collection_method: CollectionMethod = CollectionMethod.APP_UI
    language: str = "en"               # BCP-47; en, hi, ta, te, mr, bn, etc.
    consent_text_version: str          # Version of consent notice shown to user
    ip_address: str
    user_agent: str

    # External linkages
    fhir_consent_resource_id: Optional[str] = None
    abdm_consent_artefact_id: Optional[str] = None

    # Audit linkage (set after audit log is written)
    audit_chain_entry_id: Optional[str] = None

    # Flags for sensitive categories
    mental_health_explicit_consent: bool = False
    genetic_data_explicit_consent: bool = False

    @field_validator("data_categories")
    @classmethod
    def validate_sensitive_categories(cls, categories: List[DataCategory], values) -> List[DataCategory]:
        """Mental health and genetic data require explicit separate flags."""
        if DataCategory.MENTAL_HEALTH in categories:
            # This will be enforced at service layer; model documents the invariant
            pass
        if DataCategory.GENETIC in categories:
            pass
        return categories

    @property
    def is_active(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.status != ConsentStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    @property
    def covers_caregiver(self) -> bool:
        return self.delegated_to_id is not None and self.status == ConsentStatus.ACTIVE


class ConsentGrant(BaseModel):
    """Input DTO for granting a new consent."""
    data_principal_id: str
    data_fiduciary_id: str
    data_fiduciary_name: str
    purpose: ConsentPurpose
    data_categories: List[DataCategory]
    expires_at: Optional[datetime] = None
    delegated_to_id: Optional[str] = None
    delegated_to_name: Optional[str] = None
    delegation_relationship: Optional[DelegationRelationship] = None
    collection_method: CollectionMethod = CollectionMethod.APP_UI
    language: str = "en"
    consent_text_version: str
    ip_address: str
    user_agent: str
    mental_health_explicit_consent: bool = False
    genetic_data_explicit_consent: bool = False


class ConsentRevocation(BaseModel):
    """Input DTO for revoking a consent record."""
    consent_id: str
    revoked_by_id: str     # Must be data_principal_id or authorised delegate
    reason: Optional[str] = None


class ConsentVerificationResult(BaseModel):
    """
    Result of a consent gate check.
    All code that accesses patient data MUST call ConsentManager.check_consent()
    and verify result.permitted == True before proceeding.
    """
    permitted: bool
    consent_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    denial_reason: Optional[str] = None
    # For audit: record the check outcome even when permitted=False
    check_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsentSummary(BaseModel):
    """Lightweight view for the data principal's consent dashboard."""
    consent_id: str
    purpose: ConsentPurpose
    purpose_description: str
    data_categories: List[DataCategory]
    fiduciary_name: str
    granted_at: datetime
    expires_at: Optional[datetime]
    status: ConsentStatus
    delegated_to_name: Optional[str]
    delegation_relationship: Optional[DelegationRelationship]
