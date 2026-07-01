"""
apps/relaymed/backend/api/v1/router.py

Top-level v1 router — aggregates all RelayMed routes.
"""

from fastapi import APIRouter

from apps.relaymed.backend.api.v1.routes import (
    caregiver,
    health,
    medications,
    vitals,
    wearables,
    wellness,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(vitals.router, prefix="/vitals", tags=["vitals"])
api_router.include_router(medications.router, prefix="/medications", tags=["medications"])
api_router.include_router(caregiver.router, prefix="/caregiver", tags=["caregiver"])
api_router.include_router(wellness.router, prefix="/wellness", tags=["wellness"])
# wearables routes already carry their own /vitals/bulk & /wearables/* paths
api_router.include_router(wearables.router, tags=["wearables"])
