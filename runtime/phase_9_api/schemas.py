"""Pydantic models for the Phase 9 API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response."""

    status: str


class ThreadResponse(BaseModel):
    """One chat thread."""

    id: str
    created_at: str


class ThreadListResponse(BaseModel):
    """List of chat threads."""

    threads: List[ThreadResponse]


class MessageResponse(BaseModel):
    """One stored chat message."""

    id: str
    thread_id: str
    role: str
    content: str
    timestamp: str


class MessageListResponse(BaseModel):
    """Messages for a single thread."""

    thread_id: str
    messages: List[MessageResponse]


class PostMessageRequest(BaseModel):
    """Incoming user query for a thread."""

    query: str = Field(..., min_length=1)


class PostMessageResponse(BaseModel):
    """Assistant answer payload returned to the UI."""

    answer: str
    citation_url: Optional[str]
    footer: str
    thread_id: str
    refused: bool
