"""FastAPI application wiring thread storage to the Phase 7 answer pipeline."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from runtime.phase_5_retrieval.logging_config import setup_runtime_logger
from runtime.phase_8_threads.chat import post_user_message
from runtime.phase_8_threads.store import create_thread, get_history, list_threads
from runtime.phase_9_api.response_builder import build_post_message_response
from runtime.phase_9_api.schemas import (
    HealthResponse,
    MessageListResponse,
    MessageResponse,
    PostMessageRequest,
    PostMessageResponse,
    ThreadListResponse,
    ThreadResponse,
)

DEFAULT_CORS_ORIGINS = ["http://localhost:3000"]
DEFAULT_VERCEL_ORIGIN_REGEX = r"https://.*\.vercel\.app"
MESSAGE_LIST_LIMIT = 10_000


def _load_environment() -> None:
    """
    Load environment variables from a local .env file when present.
    """
    load_dotenv()


def _thread_exists(thread_id: str) -> bool:
    """
    Return True when the given thread id exists in SQLite storage.
    """
    return any(thread.id == thread_id for thread in list_threads())


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.
    """
    _load_environment()
    logger = setup_runtime_logger("runtime.phase_9_api")

    app = FastAPI(
        title="M2 RAG Chatbot API",
        description="Facts-only mutual fund FAQ assistant API",
        version="1.0.0",
    )

    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
    allow_origins = [
        origin.strip()
        for origin in cors_origins.split(",")
        if origin.strip()
    ] or DEFAULT_CORS_ORIGINS
    vercel_regex = os.environ.get("CORS_VERCEL_REGEX", DEFAULT_VERCEL_ORIGIN_REGEX)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=vercel_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """
        Return a simple liveness response for deploy health checks.
        """
        return HealthResponse(status="ok")

    @app.post("/threads", response_model=ThreadResponse)
    def create_thread_endpoint() -> ThreadResponse:
        """
        Create a new isolated chat thread.
        """
        thread = create_thread()
        logger.info("created thread: id=%s", thread.id)
        return ThreadResponse(id=thread.id, created_at=thread.created_at)

    @app.get("/threads", response_model=ThreadListResponse)
    def list_threads_endpoint() -> ThreadListResponse:
        """
        List all stored chat threads.
        """
        threads = [
            ThreadResponse(id=thread.id, created_at=thread.created_at)
            for thread in list_threads()
        ]
        return ThreadListResponse(threads=threads)

    @app.get("/threads/{thread_id}/messages", response_model=MessageListResponse)
    def list_messages_endpoint(thread_id: str) -> MessageListResponse:
        """
        List all messages for one thread without crossing thread boundaries.
        """
        if not _thread_exists(thread_id):
            raise HTTPException(status_code=404, detail="thread not found")

        messages = get_history(thread_id, last_n=MESSAGE_LIST_LIMIT)
        return MessageListResponse(
            thread_id=thread_id,
            messages=[
                MessageResponse(
                    id=message.id,
                    thread_id=message.thread_id,
                    role=message.role,
                    content=message.content,
                    timestamp=message.timestamp,
                )
                for message in messages
            ],
        )

    @app.post("/threads/{thread_id}/messages", response_model=PostMessageResponse)
    def post_message_endpoint(
        thread_id: str,
        body: PostMessageRequest,
    ) -> PostMessageResponse:
        """
        Accept a user query, run the safety pipeline, and persist both messages.
        """
        if not _thread_exists(thread_id):
            raise HTTPException(status_code=404, detail="thread not found")

        try:
            result = post_user_message(thread_id=thread_id, query=body.query.strip())
        except ValueError as exc:
            logger.error("post message failed: thread_id=%s error=%s", thread_id, exc)
            raise HTTPException(status_code=404, detail="thread not found") from exc

        payload = build_post_message_response(result)
        logger.info(
            "api message complete: thread_id=%s refused=%s",
            thread_id,
            payload["refused"],
        )
        return PostMessageResponse(**payload)

    return app
