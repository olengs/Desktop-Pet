from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar
from uuid import UUID

import psycopg
from psycopg.rows import DictRow

try:
    from config import config_bool, config_int
    from db import get_connection
except ImportError:  # Allows `python -m GarenaAI.main` from repo root.
    from GarenaAI.config import config_bool, config_int
    from GarenaAI.db import get_connection

logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass(frozen=True)
class MemorySettings:
    enabled: bool
    save_chat_history: bool
    max_chat_messages: int
    max_context_chars: int
    summarize_every_messages: int

    @classmethod
    def from_config(cls) -> "MemorySettings":
        max_chat_messages = max(0, config_int("GARENA_MEMORY_MAX_CHAT_MESSAGES", 8))
        return cls(
            enabled=config_bool("GARENA_MEMORY_ENABLED", True),
            save_chat_history=config_bool("GARENA_MEMORY_SAVE_CHAT_HISTORY", True),
            max_chat_messages=max_chat_messages,
            max_context_chars=max(1000, config_int("GARENA_MEMORY_MAX_CONTEXT_CHARS", 6000)),
            summarize_every_messages=max(
                0,
                config_int("GARENA_MEMORY_SUMMARIZE_EVERY_MESSAGES", max_chat_messages or 8),
            ),
        )


@dataclass(frozen=True)
class SummaryBatch:
    existing_summary: str
    chat_messages: list[dict[str, str]]
    message_ids: list[str]


class MemoryRepository:
    def __init__(
        self,
        settings: MemorySettings | None = None,
        connection: psycopg.Connection | None = None,
    ) -> None:
        self.settings = settings or MemorySettings.from_config()
        self._conn = connection
        self._conn_lock = threading.RLock()

    def ensure_user(self, display_name: str) -> UUID:
        return self._run_in_session(lambda cur: self._ensure_user_with_cursor(cur, display_name))

    def save_chat_message(
        self,
        display_name: str,
        role: str,
        content: str,
        source: str,
        request_id: str = "",
    ) -> None:
        if not self.settings.enabled or not self.settings.save_chat_history:
            return

        cleaned_content = content.strip()
        if not cleaned_content:
            return

        def save(cur: Any) -> None:
            user_id = self._ensure_user_with_cursor(cur, display_name)
            cur.execute(
                """
                INSERT INTO ai_chat_messages (user_id, role, content, source, request_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, role, cleaned_content, source or "text", request_id or None),
            )

        self._run_in_session(save)

    def build_prompt_context(self, display_name: str, user_message: str = "") -> str:
        if not self.settings.enabled:
            return ""

        def load(cur: Any) -> tuple[str, list[DictRow]] | None:
            user_id = self._fetch_user_id_by_display_name(cur, display_name)
            if user_id is None:
                return None
            return (
                self._fetch_chat_summary(cur, user_id),
                self._fetch_recent_unsummarized_chat_messages(cur, user_id),
            )

        loaded = self._run_in_session(load)
        if loaded is None:
            return "Conversation memory for this player: no prior chat history yet."

        summary, chat_messages = loaded

        sections = ["Conversation memory for this player:"]

        if summary:
            sections.append("Rolling conversation summary:")
            sections.append(summary)

        if chat_messages:
            sections.append("Recent unsummarized chat history:")
            sections.extend(_format_chat_row(row) for row in chat_messages)

        if len(sections) == 1:
            return "Conversation memory for this player: no prior chat history yet."

        return _truncate_context("\n".join(sections), self.settings.max_context_chars)

    def pending_summary_batch(self, display_name: str) -> SummaryBatch | None:
        if (
            not self.settings.enabled
            or not self.settings.save_chat_history
            or self.settings.summarize_every_messages <= 0
        ):
            return None

        def load(cur: Any) -> tuple[str, list[DictRow]] | None:
            user_id = self._fetch_user_id_by_display_name(cur, display_name)
            if user_id is None:
                return None
            return self._fetch_chat_summary(cur, user_id), self._fetch_unsummarized_chat_messages(cur, user_id)

        loaded = self._run_in_session(load)
        if loaded is None:
            return None

        summary, rows = loaded

        if len(rows) < self.settings.summarize_every_messages:
            return None

        return SummaryBatch(
            existing_summary=summary,
            chat_messages=[_chat_row_payload(row) for row in rows],
            message_ids=[str(row["id"]) for row in rows],
        )

    def save_chat_summary(self, display_name: str, summary: str, message_ids: list[str]) -> None:
        if not self.settings.enabled or not summary.strip() or not message_ids:
            return

        message_uuids = [UUID(message_id) for message_id in message_ids]

        def save(cur: Any) -> None:
            user_id = self._ensure_user_with_cursor(cur, display_name)
            cur.execute(
                """
                UPDATE ai_chat_messages
                SET summarized_at = now()
                WHERE user_id = %s
                  AND id = ANY(%s::uuid[])
                  AND summarized_at IS NULL
                """,
                (user_id, message_uuids),
            )
            summarized_count = cur.rowcount or 0
            if summarized_count <= 0:
                return

            cur.execute(
                """
                INSERT INTO ai_chat_summaries (user_id, summary, summarized_message_count)
                VALUES (%s, %s, %s)
                """,
                (user_id, summary.strip(), summarized_count),
            )

        self._run_in_session(save)

    def close(self) -> None:
        with self._conn_lock:
            if self._conn is None or self._conn.closed:
                self._conn = None
                return
            self._conn.close()
            self._conn = None

    def _connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = get_connection()
        return self._conn

    def _run_in_session(self, operation: Callable[[Any], T]) -> T:
        with self._conn_lock:
            conn = self._connection()
            try:
                with conn.cursor() as cur:
                    result = operation(cur)
                conn.commit()
                return result
            except BaseException:
                if not conn.closed:
                    try:
                        conn.rollback()
                    except Exception:
                        logger.exception("failed to roll back PostgreSQL session")
                raise

    def _fetch_recent_unsummarized_chat_messages(self, cur: Any, user_id: UUID) -> list[DictRow]:
        if self.settings.max_chat_messages <= 0:
            return []

        cur.execute(
            """
            SELECT role, content, source, created_at
            FROM ai_chat_messages
            WHERE user_id = %s
              AND summarized_at IS NULL
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (user_id, self.settings.max_chat_messages),
        )
        rows = list(cur.fetchall())
        return list(reversed(rows))

    def _fetch_unsummarized_chat_messages(self, cur: Any, user_id: UUID) -> list[DictRow]:
        cur.execute(
            """
            SELECT id, role, content, source, created_at
            FROM ai_chat_messages
            WHERE user_id = %s
              AND summarized_at IS NULL
            ORDER BY created_at ASC, id ASC
            """,
            (user_id,),
        )
        return list(cur.fetchall())

    def _fetch_chat_summary(self, cur: Any, user_id: UUID) -> str:
        cur.execute(
            """
            SELECT summary
            FROM ai_chat_summaries
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return ""
        return str(row["summary"]).strip()

    def _fetch_user_id_by_display_name(self, cur: Any, display_name: str) -> UUID | None:
        cur.execute(
            """
            SELECT user_id
            FROM ai_users
            WHERE display_name = %s
            """,
            (display_name,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return row["user_id"]

    def _ensure_user_with_cursor(self, cur: Any, display_name: str) -> UUID:
        cur.execute(
            """
            INSERT INTO ai_users (display_name)
            VALUES (%s)
            ON CONFLICT (display_name) DO UPDATE
            SET updated_at = now()
            RETURNING user_id
            """,
            (display_name,),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("failed to create or fetch AI user")
        return row["user_id"]


def _format_chat_row(row: DictRow) -> str:
    role = "Mimo" if row["role"] == "assistant" else str(row["role"]).title()
    content = _compact_text(str(row["content"]), 280)
    return f"- {role}: {content}"


def _chat_row_payload(row: Mapping[str, Any]) -> dict[str, str]:
    return {
        "role": str(row["role"]),
        "content": str(row["content"]),
        "source": str(row["source"]),
        "created_at": str(row["created_at"]),
    }


def _compact_text(value: str, max_length: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 3].rstrip() + "..."


def _truncate_context(context: str, max_chars: int) -> str:
    if len(context) <= max_chars:
        return context
    truncated = context[: max_chars - 42].rsplit("\n", 1)[0].rstrip()
    return f"{truncated}\n[Memory context truncated by settings.]"
