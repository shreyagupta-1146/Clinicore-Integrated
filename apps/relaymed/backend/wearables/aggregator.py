"""
apps/relaymed/backend/wearables/aggregator.py

Multi-device aggregator webhook verification (Plane B).

Aggregators (Terra, Spike, Rook, Validic) push new data to a webhook you
register. They sign each request; we MUST verify the signature before trusting
the body, otherwise anyone could POST fake vitals for a patient.

Terra signs with HMAC-SHA256 over the raw body using your webhook secret and
sends it in the `terra-signature` header as `t=<ts>,v1=<hmac>`. Other providers
use a plain HMAC header; verify_signature handles the common HMAC case and the
Terra `t=,v1=` format.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def verify_signature(raw_body: bytes, header_value: str, secret: str) -> bool:
    """
    Constant-time verification of an inbound aggregator webhook.
    Accepts both a bare hex HMAC and Terra's `t=<ts>,v1=<hmac>` format.
    """
    if not secret or not header_value:
        return False

    provided = header_value
    signed_payload = raw_body

    if "v1=" in header_value:  # Terra style: t=<ts>,v1=<sig>
        parts = dict(p.split("=", 1) for p in header_value.split(",") if "=" in p)
        provided = parts.get("v1", "")
        ts = parts.get("t", "")
        signed_payload = f"{ts}.".encode() + raw_body  # Terra signs `{t}.{body}`

    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    ok = hmac.compare_digest(expected, provided)
    if not ok:
        logger.warning("aggregator_webhook_bad_signature")
    return ok
