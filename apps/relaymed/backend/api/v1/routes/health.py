"""
apps/relaymed/backend/api/v1/routes/health.py

Liveness + readiness endpoints for Kubernetes health probes.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/live")
async def liveness():
    return {"status": "ok"}


@router.get("/ready")
async def readiness():
    return {"status": "ok"}
