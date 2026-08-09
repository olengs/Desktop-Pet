from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from psycopg.rows import DictRow
from psycopg.types.json import Jsonb

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
    save_game_history: bool
    max_chat_messages: int
    max_game_events: int
    max_memories: int
    max_context_chars: int

    @classmethod
    def from_config(cls) -> "MemorySettings":
        return cls(
            enabled=config_bool("GARENA_MEMORY_ENABLED", True),
            save_chat_history=config_bool("GARENA_MEMORY_SAVE_CHAT_HISTORY", True),
            save_game_history=config_bool("GARENA_MEMORY_SAVE_GAME_HISTORY", True),
            max_chat_messages=max(0, config_int("GARENA_MEMORY_MAX_CHAT_MESSAGES", 8)),
            max_game_events=max(0, config_int("GARENA_MEMORY_MAX_GAME_EVENTS", 8)),
            max_memories=max(0, config_int("GARENA_MEMORY_MAX_MEMORIES", 6)),
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

    def save_game_history(
        self,
        user_id: str,
        game_name: str,
        averaged_stats: Mapping[str, Any],
        event_type: str = "",
        summary: str = "",
        request_id: str = "",
        match_id: str = "",
        source: str = "desktop_pet",
    ) -> None:
        if not self.settings.enabled or not self.settings.save_game_history:
            return

        normalized_stats = _normalize_json_object(averaged_stats)
        clean_game_name = game_name.strip() or "Garena"
        clean_event_type = event_type.strip() or "game_event"
        clean_summary = summary.strip() or f"{clean_game_name} event: {clean_event_type}"

        with get_connection() as conn:
            with conn.cursor() as cur:
                self._ensure_user_with_cursor(cur, user_id)
                cur.execute(
                    """
                    INSERT INTO ai_game_history (
                        user_id,
                        game_name,
                        averaged_stats,
                        event_type,
                        match_id,
                        summary,
                        source,
                        request_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        clean_game_name,
                        Jsonb(normalized_stats),
                        clean_event_type,
                        match_id.strip() or None,
                        clean_summary,
                        source or "desktop_pet",
                        request_id or None,
                    ),
                )
                game_history_id = cur.fetchone()["id"]
                if normalized_stats:
                    cur.execute(
                        """
                        INSERT INTO ai_game_stats (user_id, game_name, averaged_stats)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, game_name) DO UPDATE
                        SET averaged_stats = EXCLUDED.averaged_stats,
                            updated_at = now()
                        """,
                        (user_id, clean_game_name, Jsonb(normalized_stats)),
                    )

                self._upsert_memory_with_cursor(
                    cur,
                    user_id=user_id,
                    memory_type="game_event",
                    game_name=clean_game_name,
                    summary=clean_summary,
                    traits_affected=list(normalized_stats.keys()),
                    source_type="game_history",
                    source_id=game_history_id,
                    importance=0.6,
                    confidence=0.75,
                )

    def build_prompt_context(self, user_id: str, user_message: str = "") -> str:
        if not self.settings.enabled:
            return ""

        with get_connection() as conn:
            with conn.cursor() as cur:
                traits = self._fetch_traits(cur, user_id)
                memories = self._fetch_memories(cur, user_id)
                game_events = self._fetch_game_events(cur, user_id)
                chat_messages = self._fetch_chat_messages(cur, user_id, user_message)

        sections = ["Database memory for this player:"]

        if traits:
            sections.append("Latest averaged game stats:")
            sections.extend(_format_trait_row(row) for row in traits)

        if memories:
            sections.append("Long-term memory summaries:")
            sections.extend(_format_memory_row(row) for row in memories)

        if game_events:
            sections.append("Recent game history:")
            sections.extend(_format_game_history_row(row) for row in game_events)

        if chat_messages:
            sections.append("Recent chat history:")
            sections.extend(_format_chat_row(row) for row in chat_messages)

        if len(sections) == 1:
            return "Database memory for this player: no stored memories yet."

        return _truncate_context("\n".join(sections), self.settings.max_context_chars)

    def _fetch_traits(self, cur: Any, user_id: str) -> list[DictRow]:
        cur.execute(
            """
            SELECT game_name, averaged_stats, updated_at
            FROM ai_game_stats
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            (user_id, max(self.settings.max_game_events, 1)),
        )
        return list(cur.fetchall())

    def _fetch_memories(self, cur: Any, user_id: str) -> list[DictRow]:
        if self.settings.max_memories <= 0:
            return []

        cur.execute(
            """
            SELECT id, memory_type, game_name, summary, importance, confidence, updated_at
            FROM ai_memories
            WHERE user_id = %s
            ORDER BY importance DESC, updated_at DESC
            LIMIT %s
            """,
            (user_id, self.settings.max_memories),
        )
        rows = list(cur.fetchall())
        if rows:
            cur.execute(
                """
                UPDATE ai_memories
                SET last_used_at = now()
                WHERE id = ANY(%s)
                """,
                ([row["id"] for row in rows],),
            )
        return rows

    def _fetch_game_events(self, cur: Any, user_id: str) -> list[DictRow]:
        if self.settings.max_game_events <= 0:
            return []

        cur.execute(
            """
            SELECT game_name, event_type, summary, averaged_stats, created_at
            FROM ai_game_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, self.settings.max_game_events),
        )
        return list(reversed(cur.fetchall()))

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

    def _upsert_memory_with_cursor(
        self,
        cur: Any,
        user_id: str,
        memory_type: str,
        game_name: str | None,
        summary: str,
        traits_affected: Iterable[str],
        source_type: str,
        source_id: Any,
        importance: float,
        confidence: float,
    ) -> None:
        cur.execute(
            """
            INSERT INTO ai_memories (
                user_id,
                memory_type,
                game_name,
                summary,
                traits_affected,
                source_type,
                source_id,
                importance,
                confidence,
                last_seen_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id, memory_type, source_type, summary_hash) DO UPDATE
            SET times_observed = ai_memories.times_observed + 1,
                confidence = GREATEST(ai_memories.confidence, EXCLUDED.confidence),
                importance = GREATEST(ai_memories.importance, EXCLUDED.importance),
                traits_affected = EXCLUDED.traits_affected,
                source_id = EXCLUDED.source_id,
                last_seen_at = now(),
                updated_at = now()
            """,
            (
                user_id,
                memory_type,
                game_name,
                summary,
                Jsonb(list(traits_affected)),
                source_type,
                source_id,
                importance,
                confidence,
            ),
        )


def _normalize_json_object(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if key is None:
            continue
        normalized[str(key)] = item
    return normalized


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


def _format_trait_row(row: Mapping[str, Any]) -> str:
    return f"- {row['game_name']}: {_format_stats(row['averaged_stats'])}"


def _format_memory_row(row: Mapping[str, Any]) -> str:
    game = f" [{row['game_name']}]" if row.get("game_name") else ""
    return f"- {row['memory_type']}{game}: {row['summary']}"


def _format_game_history_row(row: Mapping[str, Any]) -> str:
    event_type = row.get("event_type") or "game_event"
    summary = row.get("summary") or "No summary"
    stats = _format_stats(row.get("averaged_stats") or {})
    return f"- {row['game_name']} {event_type}: {summary}. Stats: {stats}"


def _format_chat_row(row: Mapping[str, Any]) -> str:
    role = "Mimo" if row["role"] == "assistant" else str(row["role"]).title()
    content = _compact_text(str(row["content"]), 280)
    return f"- {role}: {content}"


def _format_stats(stats: Any) -> str:
    if not isinstance(stats, Mapping) or not stats:
        return "no stats"
    return ", ".join(f"{key}={value}" for key, value in stats.items())


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
