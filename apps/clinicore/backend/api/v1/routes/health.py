"""apps/clinicore/backend/api/v1/routes/health.py — liveness/readiness probes."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness():
    return {"status": "ok"}


@router.get("/readyz")
async def readiness(request: Request):
    onprem_ok = await request.app.state.model_gateway.onprem_health_check()
    return {
        "status": "ok" if onprem_ok else "degraded",
        "onprem_llm_reachable": onprem_ok,
    }
