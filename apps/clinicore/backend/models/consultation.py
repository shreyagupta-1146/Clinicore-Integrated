"""
apps/clinicore/backend/models/consultation.py

Chat-session persistence for clinician/AI consultations.

Continuation chains (continuation_parent_id / continuation_depth) implement
the "start a fresh-context follow-up without losing the thread" pattern
from the original Clinicore repo — capped by MAX_CONTINUATION_DEPTH so a
chain cannot grow unbounded (each continuation re-summarises rather than
replaying full history, keeping token costs bounded).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from substrate.db.base import Base


class ChatSessionORM(Base):
    __tablename__ = "clinicore_chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))

    patient_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    clinician_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    clinic_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(256), nullable=False, default="New consultation")

    continuation_parent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    continuation_depth: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    archived: Mapped[bool] = mapped_column(default=False)

    messages: Mapped[List["ChatMessageORM"]] = relationship(
        back_populates="session", order_by="ChatMessageORM.created_at"
    )


class ChatMessageORM(Base):
    __tablename__ = "clinicore_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clinicore_chat_sessions.session_id"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "clinician" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Populated only for assistant messages
    sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    grounding_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    route_used: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    escalation_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped["ChatSessionORM"] = relationship(back_populates="messages")
