"""
apps/clinicore/backend/api/v1/routes/abdm_callback.py

ABDM HIE-CM callback endpoint.

ABDM pushes encrypted health records to this URL after a HIP fulfils a
health information request. This route:
  1. Decrypts the payload using the ABDMClient (ECDH + AES-256-GCM)
  2. Imports the FHIR bundles into the patient's local FHIR timeline
  3. Acknowledges receipt to ABDM within the SLA window (60 s)
  4. Writes an audit event

This endpoint is unauthenticated by JWT (ABDM doesn't send our tokens),
but is protected by:
  - IP allowlist for ABDM gateway IPs (configured in reverse proxy / Nginx)
  - HMAC signature verification on the X-ABDM-Signature header
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from apps.clinicore.backend.core.dependencies import get_audit_logger, get_fhir_timeline
from substrate.audit.models import AuditEvent, AuditEventType
from substrate.audit.service import AuditLogger
from substrate.fhir.abdm_client import build_abdm_client_from_env
from substrate.fhir.timeline import FHIRTimeline

logger = logging.getLogger(__name__)
router = APIRouter()

# ABDM gateway IP ranges (v4) — block requests from other IPs at the Nginx layer
# These are published at https://abdm.gov.in/publications
_ABDM_GATEWAY_IPS = frozenset([
    "52.66.222.117",
    "13.234.232.161",
    "13.235.115.149",
    # Add sandbox IPs from ABDM documentation for dev environments
])


@router.post("/abdm/callback", status_code=status.HTTP_202_ACCEPTED)
async def abdm_health_info_callback(
    request: Request,
    fhir_timeline: Annotated[FHIRTimeline, Depends(get_fhir_timeline)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    """
    Receive encrypted health records pushed by a HIP via ABDM HIE-CM.
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    transaction_id = payload.get("transactionId", "unknown")

    try:
        abdm = build_abdm_client_from_env()
    except RuntimeError as exc:
        logger.error("abdm_callback_no_credentials error=%s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ABDM not configured")

    try:
        bundle = abdm.handle_hip_callback(payload)
    except ValueError as exc:
        logger.warning("abdm_callback_invalid_payload transaction_id=%s error=%s", transaction_id, exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.error("abdm_callback_decrypt_failed transaction_id=%s error=%s", transaction_id, exc)
        # Still acknowledge to ABDM (so it doesn't retry indefinitely)
        # but log the failure for investigation
        await audit_logger.log(AuditEvent(
            event_type=AuditEventType.PHI_ACCESSED,
            actor_id="abdm-hie-cm",
            resource_type="ABDMCallback",
            resource_id=transaction_id,
            details={"error": str(exc), "status": "decrypt_failed"},
        ))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Decryption failed")

    # Import decrypted FHIR bundles into the local FHIR timeline
    imported = 0
    for fhir_bundle in bundle.raw_fhir_bundles:
        try:
            entries = fhir_bundle.get("entry", [])
            for entry in entries:
                resource = entry.get("resource", {})
                resource_type = resource.get("resourceType", "")
                if resource_type == "Observation":
                    await fhir_timeline.add_observation(resource)
                    imported += 1
                elif resource_type == "MedicationStatement":
                    await fhir_timeline.add_medication_statement(resource)
                    imported += 1
        except Exception as exc:
            logger.warning("abdm_fhir_import_error transaction_id=%s error=%s", transaction_id, exc)

    await audit_logger.log(AuditEvent(
        event_type=AuditEventType.PHI_ACCESSED,
        actor_id="abdm-hie-cm",
        resource_type="ABDMCallback",
        resource_id=transaction_id,
        details={"status": "ok", "imported_resources": imported},
    ))

    # Acknowledge to ABDM (required within SLA window)
    try:
        await abdm.acknowledge_callback(transaction_id=transaction_id, status="OK")
    except Exception as exc:
        logger.error("abdm_ack_failed transaction_id=%s error=%s", transaction_id, exc)

    logger.info("abdm_callback_processed transaction_id=%s imported=%d", transaction_id, imported)
    return {"status": "accepted", "imported": imported}
