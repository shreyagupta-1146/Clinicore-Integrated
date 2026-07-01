"""
apps/clinicore/backend/main.py

Clinicore (B2B) FastAPI application entrypoint.

Startup wires the long-lived singletons (Vault client, audit hash-chain,
hybrid model gateway, research retriever) once and attaches them to
app.state; see core/dependencies.py for how routes consume them.

Table creation here uses Base.metadata.create_all for development
convenience. Production deploys must use Alembic migrations
(infrastructure/ci/ — migration scripts are tracked separately so schema
changes are reviewable and reversible, unlike a blind create_all).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.clinicore.backend.api.v1.router import api_router
from apps.clinicore.backend.core.config import get_settings
from substrate.audit.chain import AuditChain
from substrate.audit.service import AuditLogger
from substrate.db.base import Base, get_engine
from substrate.encryption.vault_client import VaultClient
from substrate.model_gateway.router import ModelGateway

from ai_services.clinical_reasoning.research_retrieval import ResearchRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    vault = VaultClient(
        url=settings.vault_url,
        token=settings.vault_token,
        mount_path=settings.vault_mount_path,
    )

    audit_chain = AuditChain(vault=vault, immudb_host=settings.immudb_host, immudb_port=settings.immudb_port)
    await audit_chain.initialise()
    audit_logger = AuditLogger(chain=audit_chain)

    model_gateway = ModelGateway.create(
        anthropic_api_key=settings.anthropic_api_key,
        cloud_model=settings.claude_model,
        onprem_url=settings.onprem_llm_url,
        onprem_model=settings.onprem_llm_model,
        phi_risk_threshold=settings.phi_risk_threshold,
        gateway_mode=settings.model_gateway_mode,
    )

    research_retriever = ResearchRetriever(
        contact_email=settings.pubmed_email,
        api_key=settings.pubmed_api_key,
    )

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.vault = vault
    app.state.audit_logger = audit_logger
    app.state.model_gateway = model_gateway
    app.state.research_retriever = research_retriever

    logger.info("clinicore_backend_started environment=%s", settings.environment)
    yield

    await engine.dispose()
    logger.info("clinicore_backend_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Clinicore",
        description="B2B clinical decision-support platform — hybrid-sovereignty AI for clinicians.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
