"""apps/clinicore/backend/api/v1/router.py — aggregates all v1 routes."""

from __future__ import annotations

from fastapi import APIRouter

from apps.clinicore.backend.api.v1.routes import abdm_callback, consent, consultations, health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(consultations.router)
api_router.include_router(consent.router)
api_router.include_router(abdm_callback.router, tags=["abdm"])
