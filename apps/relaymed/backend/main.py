"""
apps/relaymed/backend/main.py

RelayMed (B2C) FastAPI application entrypoint.

RelayMed is the consumer-facing app: patients and caregivers interact here.
It writes to the shared FHIR timeline and fires alerts; Clinicore reads from
that same timeline during clinical consultations.

Key differences vs Clinicore:
  - Users are patients + caregivers, not clinicians
  - Safety validator operates in consumer mode (full emergency block)
  - No direct LLM access for raw-PHI clinical reasoning (that lives in Clinicore)
  - RelayMed does have a limited AI layer for personalised adherence nudges,
    which routes only de-identified data to the cloud model gateway
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.relaymed.backend.api.v1.router import api_router
from apps.relaymed.backend.core.config import get_settings
from substrate.audit.chain import AuditChain
from substrate.audit.service import AuditLogger
from substrate.db.base import Base, get_engine
from substrate.encryption.vault_client import VaultClient

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

    audit_chain = AuditChain(
        vault=vault,
        immudb_host=settings.immudb_host,
        immudb_port=settings.immudb_port,
    )
    await audit_chain.initialise()
    audit_logger = AuditLogger(chain=audit_chain)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.vault = vault
    app.state.audit_logger = audit_logger

    logger.info("relaymed_backend_started environment=%s", settings.environment)
    yield

    await engine.dispose()
    logger.info("relaymed_backend_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="RelayMed",
        description="B2C chronic-disease companion — vitals tracking, medication adherence, and caregiver coordination.",
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
