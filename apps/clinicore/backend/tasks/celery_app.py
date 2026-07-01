"""
apps/clinicore/backend/tasks/celery_app.py

Celery app shared by Clinicore and RelayMed background workers (see
docker-compose.yml celery-worker: -Q clinicore,relaymed). Two queues on one
worker pool for the MVP; split into separate worker deployments once task
volume justifies the operational overhead.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from apps.clinicore.backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "clinicore",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_routes={
        "apps.clinicore.backend.tasks.*": {"queue": "clinicore"},
        "apps.relaymed.backend.tasks.*": {"queue": "relaymed"},
    },
)

celery_app.conf.beat_schedule = {
    "onprem-llm-health-check": {
        "task": "apps.clinicore.backend.tasks.maintenance.check_onprem_llm_health",
        "schedule": crontab(minute="*/5"),
    },
    "audit-chain-tip-snapshot": {
        "task": "apps.clinicore.backend.tasks.maintenance.snapshot_audit_chain_tip",
        "schedule": crontab(minute=0),  # hourly
    },
}
