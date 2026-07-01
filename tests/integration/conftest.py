"""
tests/integration/conftest.py

Shared fixtures for integration tests.

These tests require a real Postgres database. The CI pipeline starts Postgres
via docker-compose before running this suite (see infrastructure/ci/github-actions.yml).
For local runs: docker compose up -d postgres redis vault immudb

All tests use a transaction that is rolled back after each test, so the
database is left clean without needing a full reset between tests.
"""

from __future__ import annotations

import os
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from substrate.db.base import Base
from substrate.audit.models import AuditEvent, AuditEventType
from substrate.audit.service import AuditLogger


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set — skipping integration tests")
    return url


@pytest_asyncio.fixture(scope="session")
async def db_engine(database_url):
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    """
    Yields a session with a savepoint. All changes are rolled back after
    each test — database is clean for the next test without a full reset.
    """
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            await session.begin_nested()   # savepoint
            yield session
            await session.rollback()       # rollback to savepoint


@pytest_asyncio.fixture
async def null_audit_logger() -> AuditLogger:
    """
    AuditLogger that writes to a no-op chain — avoids needing immudb in tests.
    """
    class NullChain:
        async def append(self, event: AuditEvent) -> str:
            return "test-audit-id"

    return AuditLogger(chain=NullChain())
