"""
apps/relaymed/backend/services/notification_service.py

Caregiver alert dispatch. Replaces the original RelayMed/SentiHealth pattern
of Telegram bot notifications (a personal-chat-app integration, not viable
for a real product) with Slack webhook (for clinic/ops-side alerts) and a
push-notification stub for the patient-facing mobile app (caregiver alerts
should primarily be in-app/push, not a chat bot).

This module never decides WHETHER to alert — that's the rule engines in
rules/. It only delivers an already-decided alert and records that delivery
was attempted, so a silently-failed notification is itself visible in audit
logs (mirrors the AuditLogger "never fail silently" design).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class AlertPayload:
    caregiver_id: str
    patient_display_name: str
    title: str
    body: str
    severity: str   # "info" | "warning" | "critical"


class NotificationService:
    def __init__(self, slack_webhook_url: Optional[str] = None, push_provider_key: Optional[str] = None):
        self._slack_webhook_url = slack_webhook_url
        self._push_provider_key = push_provider_key
        self._timeout = httpx.Timeout(10.0)

    async def send_caregiver_alert(self, alert: AlertPayload) -> bool:
        """
        Returns True if delivery succeeded via at least one channel.
        Caller (the rule engine / route) is responsible for logging the
        WELLNESS_ALERT_SENT audit event with this result.
        """
        delivered = await self._send_push(alert)
        if not delivered and self._slack_webhook_url:
            # Fallback path for ops visibility during MVP (no push infra yet);
            # NOT a substitute for push in production — see README roadmap.
            delivered = await self._send_slack_fallback(alert)
        if not delivered:
            logger.error("caregiver_alert_delivery_failed caregiver_id=%s title=%s", alert.caregiver_id, alert.title)
        return delivered

    async def _send_push(self, alert: AlertPayload) -> bool:
        if not self._push_provider_key:
            logger.warning("push_provider_not_configured — alert not delivered to device")
            return False
        # Real push delivery (FCM/APNs) requires per-user device tokens, which
        # live in a device-registration table not yet built for the MVP.
        # This is an honest stub, not a fabricated "sent" result.
        logger.info("push_notification_stub caregiver_id=%s title=%s", alert.caregiver_id, alert.title)
        return False

    async def _send_slack_fallback(self, alert: AlertPayload) -> bool:
        emoji = {"info": ":information_source:", "warning": ":warning:", "critical": ":rotating_light:"}.get(
            alert.severity, ""
        )
        text = f"{emoji} *{alert.title}* — {alert.patient_display_name}\n{alert.body}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(self._slack_webhook_url, json={"text": text})
                resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("slack_alert_delivery_failed error=%s", exc)
            return False
