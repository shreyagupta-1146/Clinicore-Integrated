"""
substrate/fhir/abdm_client.py

ABDM HIE-CM (Health Information Exchange and Consent Manager) client.

Implements the ABDM HIE-CM v0.5 API specification:
  https://abdm.gov.in/publications/api-specifications

This is a PULL-then-CALLBACK architecture — not a simple REST API:
  1. We (HIU — Health Information User) send a health information request
  2. ABDM CM notifies the HIP (Health Information Provider) holding the records
  3. HIP pushes encrypted FHIR data to our registered callback URL
  4. We decrypt the pushed data using ECDH key exchange

Registration requirement:
  You must register as a Health Information User (HIU) with ABDM and receive:
    ABDM_CLIENT_ID    — issued on registration
    ABDM_CLIENT_SECRET — issued on registration
    A publicly reachable callback URL registered with ABDM

Sandbox environment for testing:
  ABDM_BASE_URL = https://dev.abdm.gov.in/gateway
  Register at: https://sandbox.abdm.gov.in/

Encryption (ABDM mandated):
  ECDH X25519 (or P-256) + HKDF-SHA256 + AES-256-GCM
  We generate an ephemeral ECDH keypair per request.
  The HIP uses our public key to derive a shared secret, encrypts data.
  We use the HIP's public key (sent in callback) + our private key to decrypt.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


@dataclass
class ABDMConfig:
    client_id: str
    client_secret: str
    base_url: str = "https://dev.abdm.gov.in/gateway"
    callback_url: str = "https://api.clinicore.in/api/v1/abdm/callback"
    hiu_id: str = ""          # Your registered HIU identifier
    hiu_name: str = "Clinicore"


@dataclass
class HealthInfoRequest:
    consent_artefact_id: str    # ABDM consent artefact granted by patient
    date_from: datetime
    date_to: datetime
    request_id: str = ""        # auto-generated if empty


@dataclass
class DecryptedHealthBundle:
    """FHIR Bundle received from a HIP, after decryption."""
    transaction_id: str
    care_contexts: List[Dict[str, Any]]
    raw_fhir_bundles: List[Dict[str, Any]]


class ABDMClient:
    """
    ABDM HIE-CM client for federated health record retrieval.

    Usage:
        client = ABDMClient(config)
        request_id = await client.request_health_info(HealthInfoRequest(...))
        # Wait for HIP to push data to your callback URL
        # Then call: bundle = client.handle_callback(callback_payload)
    """

    def __init__(self, config: ABDMConfig):
        self._config = config
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        # In-flight ephemeral ECDH keys: request_id -> X25519PrivateKey
        self._pending_keys: Dict[str, X25519PrivateKey] = {}

    # ── Authentication ────────────────────────────────────────────────────────

    async def _get_token(self) -> str:
        """Get a valid ABDM access token, refreshing if expired."""
        now = datetime.now(timezone.utc)
        if self._access_token and self._token_expiry and now < self._token_expiry:
            return self._access_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._config.base_url}/v0.5/sessions",
                json={
                    "clientId": self._config.client_id,
                    "clientSecret": self._config.client_secret,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        self._access_token = data["accessToken"]
        # ABDM tokens are valid for 30 minutes; refresh with 1 minute buffer
        self._token_expiry = now + timedelta(minutes=29)
        logger.info("abdm_auth_token_refreshed")
        return self._access_token

    def _auth_headers(self, token: str, request_id: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "X-CM-ID": "sbx",              # "sbx" for sandbox, "abdm" for prod
            "X-HIP-ID": self._config.hiu_id,
            "REQUEST-ID": request_id,
            "TIMESTAMP": datetime.now(timezone.utc).isoformat(),
            "Content-Type": "application/json",
        }

    # ── Health Information Request ────────────────────────────────────────────

    async def request_health_info(self, request: HealthInfoRequest) -> str:
        """
        Initiate a health information request via ABDM HIE-CM.
        Returns the request_id. The actual data arrives asynchronously
        via the callback URL registered with ABDM.

        ABDM flow after this call:
          1. ABDM CM validates the consent artefact
          2. ABDM notifies the HIP(s) listed in the artefact
          3. HIP fetches the artefact, validates it, encrypts and pushes data
          4. Data arrives at our callback URL (handle_hip_callback)
        """
        request_id = request.request_id or str(uuid.uuid4())
        token = await self._get_token()

        # Generate ephemeral X25519 keypair for this request
        # (ABDM mandates fresh ECDH keys per request for forward secrecy)
        private_key = X25519PrivateKey.generate()
        public_key_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        # Store private key to decrypt the callback
        self._pending_keys[request_id] = private_key

        nonce = base64.b64encode(os.urandom(32)).decode("utf-8")

        payload = {
            "requestId": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hiRequest": {
                "consent": {"id": request.consent_artefact_id},
                "dateRange": {
                    "from": request.date_from.isoformat(),
                    "to": request.date_to.isoformat(),
                },
                "dataPushUrl": self._config.callback_url,
                "keyMaterial": {
                    "cryptoAlg": "ECDH",
                    "curve": "Curve25519",
                    "dhPublicKey": {
                        "expiry": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                        "parameters": "Curve25519/32byte random key",
                        "keyValue": base64.b64encode(public_key_bytes).decode("utf-8"),
                    },
                    "nonce": nonce,
                },
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._config.base_url}/v0.5/health-information/cm/request",
                json=payload,
                headers=self._auth_headers(token, request_id),
            )
            resp.raise_for_status()

        logger.info("abdm_hir_sent request_id=%s consent=%s", request_id, request.consent_artefact_id)
        return request_id

    # ── Callback Handler (receives encrypted data from HIP) ───────────────────

    def handle_hip_callback(self, callback_payload: Dict[str, Any]) -> DecryptedHealthBundle:
        """
        Decrypt and parse health records pushed by a HIP to our callback URL.

        callback_payload is the raw JSON body of the ABDM health-information/transfer
        POST request. It contains:
          - transaction_id
          - entries[]: encrypted FHIR care context bundles
          - keyMaterial: HIP's ECDH public key + nonce (needed for ECDH decryption)

        This method is called from the FastAPI route that handles ABDM callbacks.
        """
        transaction_id = callback_payload.get("transactionId", "")
        entries = callback_payload.get("entries", [])
        key_material = callback_payload.get("keyMaterial", {})
        request_id = callback_payload.get("requestId", "")

        # Retrieve our ephemeral private key for this request
        private_key = self._pending_keys.pop(request_id, None)
        if private_key is None:
            raise ValueError(
                f"No pending ECDH private key for request_id={request_id}. "
                "Possible replay or unknown request."
            )

        # Extract HIP's X25519 public key and nonce
        hip_pubkey_b64 = key_material.get("dhPublicKey", {}).get("keyValue", "")
        hip_nonce = key_material.get("nonce", "")
        if not hip_pubkey_b64 or not hip_nonce:
            raise ValueError("ABDM callback missing HIP key material")

        hip_pubkey_bytes = base64.b64decode(hip_pubkey_b64)
        hip_public_key = X25519PrivateKey.from_private_bytes(b"\x00" * 32).public_key().__class__
        # Proper X25519 public key loading:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
        hip_public_key = X25519PublicKey.from_public_bytes(hip_pubkey_bytes)

        # ECDH: our private key × HIP's public key → shared secret
        shared_secret = private_key.exchange(hip_public_key)

        # HKDF to derive decryption key (ABDM spec: SHA-256, no salt, no info)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=base64.b64decode(hip_nonce),
            info=b"",
        )
        decryption_key = hkdf.derive(shared_secret)

        # Decrypt each care context entry
        raw_fhir_bundles = []
        care_contexts = []
        for entry in entries:
            care_context_ref = entry.get("careContextReference", "")
            encrypted_content = entry.get("content", "")
            if not encrypted_content:
                continue
            try:
                fhir_bundle = self._decrypt_entry(
                    encrypted_content=encrypted_content,
                    decryption_key=decryption_key,
                )
                raw_fhir_bundles.append(fhir_bundle)
                care_contexts.append({"reference": care_context_ref, "decrypted": True})
            except Exception as exc:
                logger.error(
                    "abdm_entry_decrypt_failed care_context=%s error=%s",
                    care_context_ref, exc,
                )
                care_contexts.append({"reference": care_context_ref, "decrypted": False, "error": str(exc)})

        logger.info(
            "abdm_callback_handled transaction_id=%s entries=%d decrypted=%d",
            transaction_id, len(entries), len(raw_fhir_bundles),
        )
        return DecryptedHealthBundle(
            transaction_id=transaction_id,
            care_contexts=care_contexts,
            raw_fhir_bundles=raw_fhir_bundles,
        )

    def _decrypt_entry(self, encrypted_content: str, decryption_key: bytes) -> Dict[str, Any]:
        """
        Decrypt a single care context entry.
        ABDM uses AES-256-GCM with a 12-byte IV prepended to the ciphertext.
        Content is base64-encoded: IV (12 bytes) + ciphertext + GCM tag (16 bytes).
        """
        raw = base64.b64decode(encrypted_content)
        iv = raw[:12]
        ciphertext_with_tag = raw[12:]
        aesgcm = AESGCM(decryption_key)
        plaintext = aesgcm.decrypt(iv, ciphertext_with_tag, associated_data=None)
        return json.loads(plaintext.decode("utf-8"))

    # ── Consent Status ────────────────────────────────────────────────────────

    async def get_consent_status(self, consent_request_id: str) -> Dict[str, Any]:
        """
        Check the status of a consent request we initiated via ABDM.
        Returns the raw ABDM response including status and artefact IDs.
        """
        token = await self._get_token()
        request_id = str(uuid.uuid4())
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._config.base_url}/v0.5/consents/fetch/{consent_request_id}",
                headers=self._auth_headers(token, request_id),
            )
            resp.raise_for_status()
            return resp.json()

    # ── ABDM Callback Acknowledgement ─────────────────────────────────────────

    async def acknowledge_callback(self, transaction_id: str, status: str = "OK") -> None:
        """
        Acknowledge receipt of health data to ABDM CM.
        ABDM requires an acknowledgement within the SLA window (typically 60 s).
        """
        token = await self._get_token()
        request_id = str(uuid.uuid4())
        payload = {
            "requestId": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "acknowledgement": {
                "status": status,
                "transactionId": transaction_id,
            },
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._config.base_url}/v0.5/health-information/notify",
                json=payload,
                headers=self._auth_headers(token, request_id),
            )
            resp.raise_for_status()
        logger.info("abdm_callback_acknowledged transaction_id=%s status=%s", transaction_id, status)


def build_abdm_client_from_env() -> ABDMClient:
    """
    Instantiate ABDMClient from environment variables.
    Required:
      ABDM_CLIENT_ID, ABDM_CLIENT_SECRET
    Optional:
      ABDM_BASE_URL (defaults to sandbox), ABDM_CALLBACK_URL, ABDM_HIU_ID
    """
    client_id = os.environ.get("ABDM_CLIENT_ID", "")
    client_secret = os.environ.get("ABDM_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError(
            "ABDM_CLIENT_ID and ABDM_CLIENT_SECRET are required. "
            "Register at https://sandbox.abdm.gov.in/ for sandbox credentials."
        )
    return ABDMClient(ABDMConfig(
        client_id=client_id,
        client_secret=client_secret,
        base_url=os.environ.get("ABDM_BASE_URL", "https://dev.abdm.gov.in/gateway"),
        callback_url=os.environ.get("ABDM_CALLBACK_URL", "https://api.clinicore.in/api/v1/abdm/callback"),
        hiu_id=os.environ.get("ABDM_HIU_ID", ""),
        hiu_name=os.environ.get("ABDM_HIU_NAME", "Clinicore"),
    ))
