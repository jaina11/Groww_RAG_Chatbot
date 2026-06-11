"""SQLite persistence for chat threads and messages."""

from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

DEFAULT_DB_PATH = "data/threads.db"
DEFAULT_MAX_TURNS = 6


@dataclass(frozen=True)
class ThreadRecord:
    """One persisted conversation thread."""

    id: str
    created_at: str


@dataclass(frozen=True)
class MessageRecord:
    """One message within a thread."""

    id: str
    thread_id: str
    role: str
    content: str
    timestamp: str


def _db_path(db_path: Optional[str] = None) -> Path:
    """
    Resolve the SQLite database path from the environment or default.
    """
    return Path(db_path or os.environ.get("THREAD_DB_PATH", DEFAULT_DB_PATH))


def _utc_now_iso() -> str:
    """
    Return the current UTC timestamp in ISO-8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Open a SQLite connection and ensure schema tables exist.
    """
    path = _db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES threads(id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_thread_timestamp
        ON messages (thread_id, timestamp)
        """
    )
    connection.commit()
    return connection


def create_thread(db_path: Optional[str] = None) -> ThreadRecord:
    """
    Create a new opaque UUID thread with no shared memory across threads.
    """
    thread_id = str(uuid.uuid4())
    created_at = _utc_now_iso()
    with _connect(db_path) as connection:
        connection.execute(
            "INSERT INTO threads (id, created_at) VALUES (?, ?)",
            (thread_id, created_at),
        )
        connection.commit()
    return ThreadRecord(id=thread_id, created_at=created_at)


def add_message(
    thread_id: str,
    role: str,
    content: str,
    db_path: Optional[str] = None,
) -> MessageRecord:
    """
    Append one message to a single thread without affecting other threads.
    """
    message_id = str(uuid.uuid4())
    timestamp = _utc_now_iso()
    with _connect(db_path) as connection:
        thread = connection.execute(
            "SELECT id FROM threads WHERE id = ?",
            (thread_id,),
        ).fetchone()
        if thread is None:
            raise ValueError(f"thread not found: {thread_id}")

        connection.execute(
            """
            INSERT INTO messages (id, thread_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, thread_id, role, content, timestamp),
        )
        connection.commit()
    return MessageRecord(
        id=message_id,
        thread_id=thread_id,
        role=role,
        content=content,
        timestamp=timestamp,
    )


def get_history(
    thread_id: str,
    last_n: int | None = None,
    db_path: Optional[str] = None,
) -> List[MessageRecord]:
    """
    Return the most recent messages for one thread only.

    Defaults to THREAD_MAX_TURNS (6) messages when last_n is not provided.
    """
    if last_n is None:
        last_n = int(os.environ.get("THREAD_MAX_TURNS", DEFAULT_MAX_TURNS))

    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, thread_id, role, content, timestamp
            FROM messages
            WHERE thread_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (thread_id, last_n),
        ).fetchall()

    messages = [
        MessageRecord(
            id=str(row["id"]),
            thread_id=str(row["thread_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            timestamp=str(row["timestamp"]),
        )
        for row in rows
    ]
    messages.reverse()
    return messages


def list_threads(db_path: Optional[str] = None) -> List[ThreadRecord]:
    """
    List all threads ordered by creation time descending.
    """
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, created_at
            FROM threads
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [
        ThreadRecord(id=str(row["id"]), created_at=str(row["created_at"]))
        for row in rows
    ]
