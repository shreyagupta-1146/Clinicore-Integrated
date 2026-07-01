"""
platform/audit/service.py

AuditLogger — thin async facade over AuditChain.

App code calls audit_logger.log(event); it never touches the chain directly.
The logger also writes a lightweight structured log line (for Prometheus / OpenSearch
SIEM indexing) in addition to the immudb write.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from substrate.audit.chain import AuditChain
from substrate.audit.models import AuditEntry, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, chain: AuditChain):
        self._chain = chain
        self._metrics_counter: dict[str, int] = {}  # In-process summary for Prometheus

    async def log(self, event: AuditEvent) -> str:
        """
        Append event to the WORM audit chain.
        Returns the entry_hash (use as audit_chain_entry_id in related records).

        This method is async and non-blocking; it does NOT raise on chain errors
        (it logs them instead) so a broken chain write does NOT kill a clinical workflow.
        However, chain failures ARE escalated to SecOps telemetry.
        """
        t0 = time.monotonic()
        try:
            entry_hash = await self._chain.append(event)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            self._emit_structured_log(event, entry_hash, elapsed_ms)
            self._increment_counter(event.event_type)
            return entry_hash
        except Exception as exc:
            logger.error(
                "AUDIT_CHAIN_WRITE_FAILURE event_type=%s actor=%s error=%s",
                event.event_type, event.actor_id, exc,
                exc_info=True,
            )
            # Escalate to SecOps telemetry (fire-and-forget; don't block caller)
            try:
                import asyncio
                asyncio.create_task(self._escalate_chain_failure(event, exc))
            except RuntimeError:
                pass   # No running event loop in test context
            # Return a sentinel value so callers can detect the failure
            return "AUDIT_WRITE_FAILED"

    def _emit_structured_log(self, event: AuditEvent, entry_hash: str, elapsed_ms: int) -> None:
        logger.info(
            "AUDIT event_type=%s actor=%s resource=%s/%s hash=%.16s ms=%d ip=%s",
            event.event_type.value,
            event.actor_id,
            event.resource_type,
            event.resource_id or "-",
            entry_hash,
            elapsed_ms,
            event.ip_address,
        )

    def _increment_counter(self, event_type: AuditEventType) -> None:
        key = event_type.value
        self._metrics_counter[key] = self._metrics_counter.get(key, 0) + 1

    async def _escalate_chain_failure(self, event: AuditEvent, exc: Exception) -> None:
        """Send a critical alert to SecOps when the audit chain fails to write."""
        from substrate.audit.models import AuditEvent, AuditEventType
        failure_event = AuditEvent(
            event_type=AuditEventType.SECOPS_THREAT_DETECTED,
            actor_id="system",
            resource_type="audit_chain",
            details={
                "original_event_type": event.event_type.value,
                "error": str(exc),
                "severity": "critical",
                "message": "Audit chain write failure — tamper or infrastructure fault.",
            },
            ip_address="internal",
        )
        # Write the failure notice directly to structured log only (chain is broken)
        logger.critical("AUDIT_CHAIN_FAILURE %s", failure_event.model_dump_json())
