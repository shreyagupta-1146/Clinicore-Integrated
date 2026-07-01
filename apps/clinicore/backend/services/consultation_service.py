"""
apps/clinicore/backend/services/consultation_service.py

Persists chat sessions/messages around calls to ClinicalReasoningService.
Enforces MAX_MESSAGES_PER_CHAT (forces the clinician to start a continuation
rather than growing one session's context unboundedly) and
MAX_CONTINUATION_DEPTH (caps continuation chains).
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.clinicore.backend.models.consultation import ChatMessageORM, ChatSessionORM
from ai_services.clinical_reasoning.llm_service import ClinicalReasoningService


class MessageLimitExceededError(Exception):
    pass


class ContinuationDepthExceededError(Exception):
    pass


class ConsultationService:
    def __init__(
        self,
        db: AsyncSession,
        reasoning_service: ClinicalReasoningService,
        max_messages_per_chat: int,
        max_continuation_depth: int,
    ):
        self._db = db
        self._reasoning = reasoning_service
        self._max_messages = max_messages_per_chat
        self._max_continuation_depth = max_continuation_depth

    async def ask(
        self,
        *,
        patient_id: str,
        clinician_id: str,
        clinic_id: str,
        query_text: str,
        session_id: Optional[str],
        ip_address: str,
    ):
        session = await self._get_or_create_session(
            session_id=session_id,
            patient_id=patient_id,
            clinician_id=clinician_id,
            clinic_id=clinic_id,
        )

        existing_count = await self._message_count(session.session_id)
        if existing_count >= self._max_messages:
            raise MessageLimitExceededError(
                f"Session has reached the {self._max_messages}-message limit. "
                "Start a continuation to keep going with a fresh context."
            )

        history = await self._history_as_llm_messages(session.session_id)

        clinician_message = ChatMessageORM(
            session_id=session.session_id, role="clinician", content=query_text
        )
        self._db.add(clinician_message)
        await self._db.flush()

        result = await self._reasoning.ask(
            patient_id=patient_id,
            clinician_id=clinician_id,
            clinic_id=clinic_id,
            query_text=query_text,
            conversation_history=history,
            ip_address=ip_address,
            is_clinician=True,
        )

        assistant_message = ChatMessageORM(
            session_id=session.session_id,
            role="assistant",
            content=result.response_text,
            sources=[
                {"source_id": s.source_id, "title": s.title, "journal": s.journal,
                 "pub_year": s.pub_year, "url": s.url}
                for s in result.sources
            ],
            grounding_score=(result.grounding_report.grounding_score if result.grounding_report else None),
            route_used=result.route_used,
            model_used=result.model_used,
            escalation_level=result.escalation_level.value,
        )
        self._db.add(assistant_message)
        await self._db.commit()

        return session, assistant_message, result

    async def start_continuation(
        self, *, parent_session_id: str, patient_id: str, clinician_id: str, clinic_id: str
    ) -> ChatSessionORM:
        parent = await self._get_session(parent_session_id)
        if parent is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parent session not found")

        if parent.continuation_depth + 1 > self._max_continuation_depth:
            raise ContinuationDepthExceededError(
                f"Maximum continuation depth ({self._max_continuation_depth}) reached. "
                "Start a brand-new consultation instead."
            )

        new_session = ChatSessionORM(
            patient_id=patient_id,
            clinician_id=clinician_id,
            clinic_id=clinic_id,
            title=f"{parent.title} (continued)",
            continuation_parent_id=parent.session_id,
            continuation_depth=parent.continuation_depth + 1,
        )
        self._db.add(new_session)
        await self._db.commit()
        return new_session

    async def _get_or_create_session(
        self, *, session_id: Optional[str], patient_id: str, clinician_id: str, clinic_id: str
    ) -> ChatSessionORM:
        if session_id:
            session = await self._get_session(session_id)
            if session is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
            return session

        session = ChatSessionORM(patient_id=patient_id, clinician_id=clinician_id, clinic_id=clinic_id)
        self._db.add(session)
        await self._db.flush()
        return session

    async def _get_session(self, session_id: str) -> Optional[ChatSessionORM]:
        result = await self._db.execute(
            select(ChatSessionORM).where(ChatSessionORM.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def _message_count(self, session_id: str) -> int:
        result = await self._db.execute(
            select(ChatMessageORM).where(ChatMessageORM.session_id == session_id)
        )
        return len(result.scalars().all())

    async def _history_as_llm_messages(self, session_id: str) -> List[dict]:
        result = await self._db.execute(
            select(ChatMessageORM)
            .where(ChatMessageORM.session_id == session_id)
            .order_by(ChatMessageORM.created_at)
        )
        messages = result.scalars().all()
        role_map = {"clinician": "user", "assistant": "assistant"}
        return [{"role": role_map[m.role], "content": m.content} for m in messages]
