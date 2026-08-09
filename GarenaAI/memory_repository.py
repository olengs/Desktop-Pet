from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from psycopg.rows import DictRow

try:
    from config import config_bool, config_int
    from db import get_connection
except ImportError:  # Allows `python -m GarenaAI.main` from repo root.
    from GarenaAI.config import config_bool, config_int
    from GarenaAI.db import get_connection


@dataclass(frozen=True)
class MemorySettings:
    enabled: bool
    save_chat_history: bool
    max_chat_messages: int
    max_context_chars: int

    @classmethod
    def from_config(cls) -> "MemorySettings":
        return cls(
            enabled=config_bool("GARENA_MEMORY_ENABLED", True),
            save_chat_history=config_bool("GARENA_MEMORY_SAVE_CHAT_HISTORY", True),
            max_chat_messages=max(0, config_int("GARENA_MEMORY_MAX_CHAT_MESSAGES", 8)),
            max_context_chars=max(1000, config_int("GARENA_MEMORY_MAX_CONTEXT_CHARS", 6000)),
        )


class MemoryRepository:
    def __init__(self, settings: MemorySettings | None = None) -> None:
        self.settings = settings or MemorySettings.from_config()

    def ensure_user(self, user_id: str) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ai_users (user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO UPDATE
                    SET updated_at = now()
                    """,
                    (user_id,),
                )

    def save_chat_message(
        self,
        user_id: str,
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

        with get_connection() as conn:
            with conn.cursor() as cur:
                self._ensure_user_with_cursor(cur, user_id)
                cur.execute(
                    """
                    INSERT INTO ai_chat_messages (user_id, role, content, source, request_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (user_id, role, cleaned_content, source or "text", request_id or None),
                )

    def build_prompt_context(self, user_id: str, user_message: str = "") -> str:
        if not self.settings.enabled:
            return ""

        with get_connection() as conn:
            with conn.cursor() as cur:
                chat_messages = self._fetch_chat_messages(cur, user_id, user_message)

        sections = ["Recent conversation context for this player:"]

        if chat_messages:
            sections.append("Recent chat history:")
            sections.extend(_format_chat_row(row) for row in chat_messages)

        if len(sections) == 1:
            return "Recent conversation context for this player: no prior chat history yet."

        return _truncate_context("\n".join(sections), self.settings.max_context_chars)

    def _fetch_chat_messages(self, cur: Any, user_id: str, user_message: str) -> list[DictRow]:
        if self.settings.max_chat_messages <= 0:
            return []

        cur.execute(
            """
            SELECT role, content, source, created_at
            FROM ai_chat_messages
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, max(self.settings.max_chat_messages * 4, self.settings.max_chat_messages, 1)),
        )
        rows = list(cur.fetchall())
        ranked_rows = _rank_relevant_chat_rows(rows, user_message)
        return list(reversed(ranked_rows[: self.settings.max_chat_messages]))

    def _ensure_user_with_cursor(self, cur: Any, user_id: str) -> None:
        cur.execute(
            """
            INSERT INTO ai_users (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO UPDATE
            SET updated_at = now()
            """,
            (user_id,),
        )


def _rank_relevant_chat_rows(rows: list[DictRow], user_message: str) -> list[DictRow]:
    tokens = _tokens(user_message)
    if not tokens:
        return rows

    scored_rows: list[tuple[int, int, DictRow]] = []
    for index, row in enumerate(rows):
        content = str(row["content"]).lower()
        score = sum(1 for token in tokens if token in content)
        scored_rows.append((score, index, row))

    scored_rows.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return [row for _, _, row in scored_rows]


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", value.lower()) if len(token) > 2}


def _format_chat_row(row: DictRow) -> str:
    role = "Mimo" if row["role"] == "assistant" else str(row["role"]).title()
    content = _compact_text(str(row["content"]), 280)
    return f"- {role}: {content}"


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
