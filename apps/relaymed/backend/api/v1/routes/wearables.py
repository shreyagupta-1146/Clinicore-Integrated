"""
apps/relaymed/backend/api/v1/routes/wearables.py

Wearable ingestion endpoints — the two planes made concrete.

  POST /vitals/bulk
      The MOBILE APP calls this after reading Android Health Connect or iOS
      HealthKit (on-device, with the user's per-category permission). It sends
      the raw records; the server normalizes → runs the same consent/FHIR/
      anomaly pipeline as manual entry. No wearable-vendor API key involved.

  POST /wearables/webhook/{provider}
      A cloud AGGREGATOR (Terra/Spike/Rook/Validic) pushes new data here. The
      request signature is verified against the webhook secret before anything
      is trusted.

  GET  /wearables/fitbit/authorize   +   GET /wearables/fitbit/callback
      Fitbit Web API OAuth (server-side pull). The callback stores the refresh
      token (encrypt in Vault per patient); a Celery job then pulls periodically.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from apps.relaymed.backend.core.config import RelayMedSettings, get_settings
from apps.relaymed.backend.core.dependencies import get_current_user_id, get_vitals_service
from apps.relaymed.backend.wearables import normalizer
from apps.relaymed.backend.wearables.aggregator import verify_signature
from apps.relaymed.backend.wearables.fitbit_client import FitbitClient

router = APIRouter()


class BulkVitalsPayload(BaseModel):
    platform: str            # "health_connect" | "apple_health"
    device: str = ""
    records: List[Dict[str, Any]]   # raw records from the on-device hub


@router.post("/vitals/bulk", status_code=status.HTTP_202_ACCEPTED)
async def ingest_bulk(
    payload: BulkVitalsPayload,
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
    vitals_service: Annotated[object, Depends(get_vitals_service)],
):
    """Mobile app posts a batch read from Health Connect (Android) / HealthKit (iOS)."""
    if payload.platform == "health_connect":
        readings = normalizer.normalize_health_connect(payload.records, device=payload.device or "Health Connect")
    elif payload.platform == "apple_health":
        readings = normalizer.normalize_healthkit(payload.records, device=payload.device or "Apple Health")
    else:
        raise HTTPException(status_code=422, detail="platform must be 'health_connect' or 'apple_health'")

    if not readings:
        return {"ingested": 0, "note": "no recognised metrics in payload"}

    result = await vitals_service.ingest_batch(
        patient_id=user_id,
        patient_display_name=user_id,
        readings=readings,
        ip_address=request.client.host if request.client else "",
    )
    return result


@router.post("/wearables/webhook/{provider}", status_code=status.HTTP_202_ACCEPTED)
async def aggregator_webhook(
    provider: str,
    request: Request,
    settings: Annotated[RelayMedSettings, Depends(get_settings)],
    vitals_service: Annotated[object, Depends(get_vitals_service)],
    terra_signature: Annotated[str | None, Header(alias="terra-signature")] = None,
    x_signature: Annotated[str | None, Header(alias="x-signature")] = None,
):
    """Aggregator (Terra/Spike/Rook/Validic) pushes new data. Signature-verified."""
    raw = await request.body()
    sig = terra_signature or x_signature or ""
    if not verify_signature(raw, sig, settings.wearable_aggregator_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    import json
    body = json.loads(raw or b"{}")
    readings = normalizer.normalize_aggregator(body)

    # The aggregator maps its own user id → our patient id; here we expect it in the body.
    patient_id = body.get("user", {}).get("reference_id") or body.get("reference_id")
    if not patient_id:
        raise HTTPException(status_code=422, detail="missing patient reference_id in webhook body")

    result = await vitals_service.ingest_batch(
        patient_id=patient_id,
        patient_display_name=patient_id,
        readings=readings,
        ip_address="aggregator",
    )
    return {"provider": provider, **result}


@router.get("/wearables/fitbit/authorize")
async def fitbit_authorize(
    user_id: Annotated[str, Depends(get_current_user_id)],
    settings: Annotated[RelayMedSettings, Depends(get_settings)],
):
    """Return the Fitbit OAuth URL the app opens to connect a Fitbit account."""
    if not settings.fitbit_client_id:
        raise HTTPException(status_code=503, detail="Fitbit not configured")
    client = FitbitClient(settings.fitbit_client_id, settings.fitbit_client_secret, settings.fitbit_redirect_uri)
    return {"authorize_url": client.authorize_url(state=user_id)}


@router.get("/wearables/fitbit/callback")
async def fitbit_callback(
    code: str,
    state: str,
    settings: Annotated[RelayMedSettings, Depends(get_settings)],
):
    """
    Fitbit redirects here after the user authorizes. Exchange the code for tokens.
    Production: encrypt the refresh_token in Vault keyed by `state` (the patient id)
    and schedule a Celery pull job. Here we return a success marker.
    """
    if not settings.fitbit_client_id:
        raise HTTPException(status_code=503, detail="Fitbit not configured")
    client = FitbitClient(settings.fitbit_client_id, settings.fitbit_client_secret, settings.fitbit_redirect_uri)
    tokens = await client.exchange_code(code)
    # TODO: vault.set_secret(f"relaymed/fitbit/{state}", tokens["refresh_token"])
    return {"connected": True, "patient": state, "scopes": tokens.get("scope", "")}
