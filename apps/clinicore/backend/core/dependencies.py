"""
apps/clinicore/backend/core/dependencies.py

FastAPI dependency providers. Long-lived singletons (ModelGateway, AuditChain,
VaultClient) are created once in main.py's lifespan handler and stored on
app.state; these functions just hand them to route handlers per-request.
Request-scoped objects (DB session, ConsentManager) are constructed fresh
each call.
"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from substrate.audit.service import AuditLogger
from substrate.consent.service import ConsentManager
from substrate.db.base import get_db
from substrate.model_gateway.router import ModelGateway

from ai_services.clinical_reasoning.llm_service import ClinicalReasoningService
from ai_services.clinical_reasoning.research_retrieval import ResearchRetriever


def get_audit_logger(request: Request) -> AuditLogger:
    return request.app.state.audit_logger


def get_model_gateway(request: Request) -> ModelGateway:
    return request.app.state.model_gateway


def get_research_retriever(request: Request) -> ResearchRetriever:
    return request.app.state.research_retriever


def get_consent_manager(
    db: AsyncSession = Depends(get_db),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> ConsentManager:
    return ConsentManager(db=db, audit_logger=audit_logger)


def get_clinical_reasoning_service(
    gateway: ModelGateway = Depends(get_model_gateway),
    consent_manager: ConsentManager = Depends(get_consent_manager),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    research_retriever: ResearchRetriever = Depends(get_research_retriever),
) -> ClinicalReasoningService:
    return ClinicalReasoningService(
        gateway=gateway,
        consent_manager=consent_manager,
        audit_logger=audit_logger,
        research_retriever=research_retriever,
    )
