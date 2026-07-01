"""
apps/clinicore/backend/tasks/maintenance.py

Periodic maintenance tasks. Kept deliberately small and real — this
replaces SentiHealth's pattern of background "churn scripts" that
generated fabricated activity; everything here does a genuine, verifiable
check and logs a genuine result.
"""

from __future__ import annotations

import asyncio
import logging

from apps.clinicore.backend.core.config import get_settings
from apps.clinicore.backend.tasks.celery_app import celery_app
from substrate.model_gateway.onprem_client import OnPremLLMClient

logger = logging.getLogger(__name__)


@celery_app.task(name="apps.clinicore.backend.tasks.maintenance.check_onprem_llm_health")
def check_onprem_llm_health() -> dict:
    settings = get_settings()
    client = OnPremLLMClient(base_url=settings.onprem_llm_url, model=settings.onprem_llm_model)
    healthy = asyncio.run(client.health_check())
    if not healthy:
        logger.error("onprem_llm_health_check FAILED model=%s url=%s", settings.onprem_llm_model, settings.onprem_llm_url)
    return {"healthy": healthy, "model": settings.onprem_llm_model}


@celery_app.task(name="apps.clinicore.backend.tasks.maintenance.snapshot_audit_chain_tip")
def snapshot_audit_chain_tip() -> dict:
    """
    Records the current audit-chain tip hash to Prometheus/logs hourly.
    This is a cheap, independent corroboration signal: if the tip stored
    here ever diverges from what immudb reports on read, that is a strong
    tamper indicator worth alerting on (see secops/detection/ for the rule).
    """
    # NOTE: requires an async AuditChain instance; wiring a worker-local
    # singleton is tracked as a follow-up — this task currently only proves
    # the schedule fires (visible in celery-beat logs) pending that wiring.
    logger.info("audit_chain_tip_snapshot_scheduled")
    return {"status": "scheduled_not_yet_wired"}
