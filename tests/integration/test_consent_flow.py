"""
tests/integration/test_consent_flow.py

Integration tests for the ConsentManager against a real Postgres database.

These tests verify the DPDP Act 2023 behavioural requirements:
  - Active consent permits access
  - Revoked consent denies access immediately
  - Expired consent is treated as revoked
  - Sensitive-category consent requires explicit flag
  - Caregiver delegation requires principal-granted consent
  - A caregiver cannot self-grant access
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone

from substrate.consent.models import (
    CollectionMethod,
    ConsentGrant,
    ConsentPurpose,
    ConsentRevocation,
    ConsentStatus,
    DataCategory,
    DelegationRelationship,
)
from substrate.consent.service import ConsentManager, SensitiveCategoryConsentError


@pytest.mark.asyncio
async def test_grant_and_check_permitted(db_session, null_audit_logger):
    """Granted active consent permits access."""
    mgr = ConsentManager(db=db_session, audit_logger=null_audit_logger)

    await mgr.grant_consent(ConsentGrant(
        data_principal_id="patient-001",
        requesting_entity_id="clinicore-backend",
        purpose=ConsentPurpose.CLINICAL_DECISION_SUPPORT,
        data_categories=[DataCategory.VITALS, DataCategory.CONDITIONS],
        collection_method=CollectionMethod.EXPLICIT_UI,
        ip_address="127.0.0.1",
    ))

    result = await mgr.check_consent(
        data_principal_id="patient-001",
        requesting_entity_id="clinicore-backend",
        purpose=ConsentPurpose.CLINICAL_DECISION_SUPPORT,
        data_categories=[DataCategory.VITALS],
    )
    assert result.permitted is True


@pytest.mark.asyncio
async def test_revoke_denies_immediately(db_session, null_audit_logger):
    """Revoked consent denies access in the same session."""
    mgr = ConsentManager(db=db_session, audit_logger=null_audit_logger)

    record = await mgr.grant_consent(ConsentGrant(
        data_principal_id="patient-002",
        requesting_entity_id="clinicore-backend",
        purpose=ConsentPurpose.WELLNESS_TRACKING,
        data_categories=[DataCategory.LIFESTYLE],
        collection_method=CollectionMethod.EXPLICIT_UI,
    ))

    await mgr.revoke_consent(ConsentRevocation(
        consent_record_id=str(record.id),
        data_principal_id="patient-002",
        reason="User withdrew consent",
    ), ip_address="127.0.0.1")

    result = await mgr.check_consent(
        data_principal_id="patient-002",
        requesting_entity_id="clinicore-backend",
        purpose=ConsentPurpose.WELLNESS_TRACKING,
        data_categories=[DataCategory.LIFESTYLE],
    )
    assert result.permitted is False
    assert "revoked" in (result.denial_reason or "").lower()


@pytest.mark.asyncio
async def test_expired_consent_denied(db_session, null_audit_logger):
    """Consent with a past expires_at is treated as revoked."""
    mgr = ConsentManager(db=db_session, audit_logger=null_audit_logger)

    past = datetime.now(timezone.utc) - timedelta(days=1)
    await mgr.grant_consent(ConsentGrant(
        data_principal_id="patient-003",
        requesting_entity_id="clinicore-backend",
        purpose=ConsentPurpose.RESEARCH_DEIDENTIFIED,
        data_categories=[DataCategory.CONDITIONS],
        collection_method=CollectionMethod.EXPLICIT_UI,
        expires_at=past,
    ))

    result = await mgr.check_consent(
        data_principal_id="patient-003",
        requesting_entity_id="clinicore-backend",
        purpose=ConsentPurpose.RESEARCH_DEIDENTIFIED,
        data_categories=[DataCategory.CONDITIONS],
    )
    assert result.permitted is False


@pytest.mark.asyncio
async def test_sensitive_category_requires_explicit_flag(db_session, null_audit_logger):
    """Mental health / genetic data requires explicit sensitive-category consent flag."""
    mgr = ConsentManager(db=db_session, audit_logger=null_audit_logger)

    with pytest.raises(SensitiveCategoryConsentError):
        await mgr.grant_consent(ConsentGrant(
            data_principal_id="patient-004",
            requesting_entity_id="clinicore-backend",
            purpose=ConsentPurpose.CLINICAL_DECISION_SUPPORT,
            data_categories=[DataCategory.MENTAL_HEALTH],
            collection_method=CollectionMethod.EXPLICIT_UI,
            # Missing: sensitive_category_explicit_flag=True
        ))


@pytest.mark.asyncio
async def test_caregiver_delegation_requires_principal_grant(db_session, null_audit_logger):
    """
    A caregiver cannot access patient data by self-assigning — the patient
    (data principal) must have granted a delegated consent record.
    """
    mgr = ConsentManager(db=db_session, audit_logger=null_audit_logger)

    # Caregiver checks without any consent being granted by the patient
    result = await mgr.check_consent(
        data_principal_id="patient-005",
        requesting_entity_id="caregiver-999",   # caregiver, not the backend service
        purpose=ConsentPurpose.CAREGIVER_MONITORING,
        data_categories=[DataCategory.VITALS],
    )
    assert result.permitted is False


@pytest.mark.asyncio
async def test_wrong_entity_denied(db_session, null_audit_logger):
    """Consent granted to entity A does not permit entity B."""
    mgr = ConsentManager(db=db_session, audit_logger=null_audit_logger)

    await mgr.grant_consent(ConsentGrant(
        data_principal_id="patient-006",
        requesting_entity_id="clinicore-backend",
        purpose=ConsentPurpose.CLINICAL_DECISION_SUPPORT,
        data_categories=[DataCategory.VITALS],
        collection_method=CollectionMethod.EXPLICIT_UI,
    ))

    result = await mgr.check_consent(
        data_principal_id="patient-006",
        requesting_entity_id="some-other-service",   # different entity
        purpose=ConsentPurpose.CLINICAL_DECISION_SUPPORT,
        data_categories=[DataCategory.VITALS],
    )
    assert result.permitted is False
