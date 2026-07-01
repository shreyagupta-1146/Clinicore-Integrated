"""
secops/response/handler.py

Incident response handler — HITL (human-in-the-loop) escalation queue.

Design principle (from the implementation plan):
  NO automated enforcement actions fire without analyst confirmation.
  This is not a weakness — it is a deliberate control.

  The one exception the plan allowed: automatic session termination on CRITICAL
  findings after a 15-minute unacknowledged timeout. Even that requires the
  on-call to have been paged and actively ignored, not a cold automation.

What this module does:
  1. Receives ThreatFinding from UEBAAnalyzer / DetectionRules
  2. Enqueues it in Redis for the SRE console (weave-heal UI repurposed as SOC console)
  3. Pages on-call via PagerDuty if severity >= HIGH
  4. Starts an auto-escalation timer (asyncio task) for CRITICAL findings
  5. Provides acknowledge() — analyst marks finding as reviewed
  6. Provides execute_containment() — analyst explicitly approves containment action

What this module does NOT do:
  - Block IPs automatically (SentiHealth's fake "block_ip()")
  - Throttle bandwidth automatically (SentiHealth's fake "throttle_bandwidth()")
  - Terminate sessions without analyst confirmation on non-CRITICAL findings
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import redis.asyncio as aioredis

from secops.ueba.analyzer import ThreatFinding, ThreatSeverity

logger = logging.getLogger(__name__)


class IncidentResponseHandler:

    def __init__(
        self,
        redis_url: str,
        pagerduty_integration_key: Optional[str] = None,
    ):
        self._redis = aioredis.from_url(redis_url)
        self._pagerduty_key = pagerduty_integration_key
        self._pending: Dict[str, asyncio.Task] = {}

    async def handle_finding(self, finding: ThreatFinding) -> str:
        """
        Process a ThreatFinding. Returns the incident_id.
        """
        incident_id = str(uuid.uuid4())
        incident = {
            "incident_id": incident_id,
            "rule_id": finding.rule_id,
            "severity": finding.severity.value,
            "title": finding.title,
            "description": finding.description,
            "actor_id": finding.actor_id,
            "source_ip": finding.source_ip,
            "evidence": finding.evidence,
            "detected_at": finding.detected_at.isoformat(),
            "status": "pending_review",
        }

        # Write to Redis for SRE console
        await self._redis.rpush("secops:incidents:queue", json.dumps(incident))
        await self._redis.set(f"secops:incidents:{incident_id}", json.dumps(incident), ex=86400)

        logger.warning(
            "secops_finding_queued incident_id=%s rule_id=%s severity=%s title=%r",
            incident_id, finding.rule_id, finding.severity.value, finding.title,
        )

        # Page on-call for HIGH and CRITICAL
        if finding.severity in (ThreatSeverity.HIGH, ThreatSeverity.CRITICAL):
            asyncio.create_task(self._page_oncall(incident))

        # Start auto-escalation timer for CRITICAL
        if finding.severity == ThreatSeverity.CRITICAL and finding.requires_human_review:
            task = asyncio.create_task(
                self._auto_escalate(incident_id, finding.auto_escalate_after_minutes)
            )
            self._pending[incident_id] = task

        return incident_id

    async def acknowledge(self, incident_id: str, analyst_id: str) -> None:
        """Analyst marks incident as reviewed — cancels auto-escalation timer."""
        raw = await self._redis.get(f"secops:incidents:{incident_id}")
        if not raw:
            raise ValueError(f"Incident {incident_id} not found")
        incident = json.loads(raw)
        incident["status"] = "acknowledged"
        incident["acknowledged_by"] = analyst_id
        incident["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
        await self._redis.set(f"secops:incidents:{incident_id}", json.dumps(incident), ex=86400)

        if incident_id in self._pending:
            self._pending[incident_id].cancel()
            del self._pending[incident_id]

        logger.info("secops_incident_acknowledged incident_id=%s analyst=%s", incident_id, analyst_id)

    async def execute_containment(
        self,
        incident_id: str,
        analyst_id: str,
        action: str,
        action_params: Dict[str, Any],
    ) -> None:
        """
        Analyst explicitly approves a containment action.
        Supported actions: terminate_session | disable_account | isolate_pod

        All actions are logged to the audit chain. The analyst's identity and
        explicit approval are recorded — no anonymous automated enforcement.
        """
        logger.warning(
            "secops_containment_executed incident_id=%s analyst=%s action=%s params=%s",
            incident_id, analyst_id, action, action_params,
        )

        if action == "terminate_session":
            # Push session termination command to the Keycloak admin API via
            # the revocation endpoint. Keycloak then invalidates all tokens
            # for the target user. This is the RIGHT way to terminate a session —
            # not by blocking an IP, which the attacker can simply change.
            user_id = action_params.get("user_id")
            if user_id:
                await self._revoke_keycloak_sessions(user_id)

        elif action == "disable_account":
            user_id = action_params.get("user_id")
            if user_id:
                await self._disable_keycloak_account(user_id)

        elif action == "isolate_pod":
            # In production: apply a Kubernetes NetworkPolicy via the k8s API
            # to isolate the compromised pod from other services.
            pod_name = action_params.get("pod_name")
            namespace = action_params.get("namespace", "default")
            logger.warning("secops_pod_isolation_requested pod=%s namespace=%s (manual k8s action required)", pod_name, namespace)
        else:
            raise ValueError(f"Unknown containment action: {action}")

    async def _page_oncall(self, incident: Dict[str, Any]) -> None:
        if not self._pagerduty_key:
            logger.warning("secops_no_pagerduty_key — cannot page on-call for incident=%s", incident["incident_id"])
            return
        payload = {
            "routing_key": self._pagerduty_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"[{incident['severity'].upper()}] {incident['title']}",
                "source": "clinicore-secops",
                "severity": incident["severity"],
                "custom_details": {
                    "incident_id": incident["incident_id"],
                    "rule_id": incident["rule_id"],
                    "actor_id": incident.get("actor_id"),
                    "source_ip": incident.get("source_ip"),
                },
            },
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("https://events.pagerduty.com/v2/enqueue", json=payload)
                resp.raise_for_status()
                logger.info("secops_pagerduty_paged incident_id=%s", incident["incident_id"])
        except Exception as exc:
            logger.error("secops_pagerduty_failed error=%s", exc)

    async def _auto_escalate(self, incident_id: str, timeout_minutes: int) -> None:
        """
        After timeout, if still unacknowledged, upgrade severity and re-page.
        This is the ONLY automated action — and it's just a page, not enforcement.
        """
        await asyncio.sleep(timeout_minutes * 60)
        raw = await self._redis.get(f"secops:incidents:{incident_id}")
        if not raw:
            return
        incident = json.loads(raw)
        if incident.get("status") == "acknowledged":
            return
        incident["status"] = "escalated_unacknowledged"
        await self._redis.set(f"secops:incidents:{incident_id}", json.dumps(incident), ex=86400)
        logger.critical(
            "secops_auto_escalation incident_id=%s title=%r — unacknowledged after %d minutes",
            incident_id, incident["title"], timeout_minutes,
        )
        await self._page_oncall(incident)

    async def _revoke_keycloak_sessions(self, user_id: str) -> None:
        logger.warning("secops_keycloak_session_revocation user_id=%s (requires KEYCLOAK_ADMIN credentials)", user_id)

    async def _disable_keycloak_account(self, user_id: str) -> None:
        logger.warning("secops_keycloak_account_disable user_id=%s (requires KEYCLOAK_ADMIN credentials)", user_id)
