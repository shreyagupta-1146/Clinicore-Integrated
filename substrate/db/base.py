"""
platform/db/base.py

Shared SQLAlchemy 2.0 declarative base + async session factory.

Single Postgres instance (see docker-compose.yml), shared across the platform
substrate (consent, audit metadata) and both apps (Clinicore, RelayMed).
Tables are namespaced by prefix (consent_, clinicore_, relaymed_) rather than
separate databases, so a single Alembic migration history stays consistent
and FK references across app boundaries (e.g., RelayMed observation ->
Clinicore consultation) are possible without cross-database joins.
"""

from __future__ import annotations

import os
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. See .env.example "
            "(postgresql+asyncpg://clinicore:clinicore@localhost:5432/clinicore)."
        )
    return url


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _database_url(),
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG",
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields a request-scoped AsyncSession."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
