"""
apps/clinicore/backend/schemas/consultation.py

Pydantic v2 request/response DTOs for the consultation API.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=8000)
    session_id: Optional[str] = None   # None = start a new session


class ResearchSourceOut(BaseModel):
    source_id: str
    title: str
    journal: str
    pub_year: Optional[int]
    url: str


class AskResponse(BaseModel):
    session_id: str
    message_id: str
    response_text: str
    sources: List[ResearchSourceOut]
    grounding_score: Optional[float]
    escalation_level: str
    red_flags: List[str]
    blocked: bool
    block_reason: Optional[str]
    route_used: Optional[str]
    model_used: Optional[str]
    latency_ms: Optional[int]


class ChatMessageOut(BaseModel):
    message_id: str
    role: str
    content: str
    grounding_score: Optional[float]
    created_at: datetime


class ChatSessionOut(BaseModel):
    session_id: str
    patient_id: str
    title: str
    created_at: datetime
    messages: List[ChatMessageOut]
