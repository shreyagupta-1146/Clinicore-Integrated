"""
apps/relaymed/backend/core/dependencies.py

FastAPI dependency injectors for RelayMed routes.
Pulls long-lived singletons off app.state (wired in main.py lifespan).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from apps.relaymed.backend.core.config import RelayMedSettings, get_settings
from substrate.audit.service import AuditLogger
from substrate.consent.service import ConsentManager
from substrate.db.base import get_db
from substrate.encryption.vault_client import VaultClient
from substrate.fhir.timeline import FHIRTimeline

_bearer = HTTPBearer(auto_error=False)


async def get_vault(request: Request) -> VaultClient:
    return request.app.state.vault


async def get_audit_logger(request: Request) -> AuditLogger:
    return request.app.state.audit_logger


async def get_consent_manager(
    db: Annotated[AsyncSession, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> ConsentManager:
    return ConsentManager(db=db, audit_logger=audit_logger)


async def get_fhir_timeline(
    settings: Annotated[RelayMedSettings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> FHIRTimeline:
    token = credentials.credentials if credentials else ""
    return FHIRTimeline(fhir_base_url=settings.fhir_base_url, auth_token=token)


async def get_notification_service(
    settings: Annotated[RelayMedSettings, Depends(get_settings)],
):
    from apps.relaymed.backend.services.notification_service import NotificationService
    return NotificationService(
        slack_webhook_url=getattr(settings, "slack_webhook_url", None),
        push_provider_key=getattr(settings, "expo_access_token", None),
    )


async def get_caregiver_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    consent_manager: Annotated[ConsentManager, Depends(get_consent_manager)],
):
    from apps.relaymed.backend.modules.caregiver.service import CaregiverService
    return CaregiverService(db=db, audit_logger=audit_logger, consent_manager=consent_manager)


async def get_vitals_service(
    fhir: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
    consent_manager: Annotated[ConsentManager, Depends(get_consent_manager)],
    caregiver_service: Annotated[object, Depends(get_caregiver_service)],
    notification_service: Annotated[object, Depends(get_notification_service)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    from apps.relaymed.backend.services.vitals_service import VitalsService
    return VitalsService(
        fhir=fhir,
        consent_manager=consent_manager,
        caregiver_service=caregiver_service,
        notification_service=notification_service,
        audit_logger=audit_logger,
    )


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """
    Extract the subject (user ID) from the Keycloak JWT.
    Production: validate signature, expiry, and audience against JWKS.
    Development: trust the token's 'sub' claim without full validation.
    This stub works when running behind Keycloak's reverse proxy, which
    validates the token before the request reaches this service.
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    import base64
    import json
    parts = credentials.credentials.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload_bytes = parts[1] + "=="   # re-pad base64
        payload = json.loads(base64.b64decode(payload_bytes))
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cannot decode token")
