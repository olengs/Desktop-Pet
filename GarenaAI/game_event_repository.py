from __future__ import annotations

import uuid
from typing import Any, Mapping, Sequence
from uuid import UUID

from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

try:
    from db import get_connection
    from memory_repository import MemoryRepository
except ImportError:  # Allows `python -m GarenaAI.game_event_repository` from repo root.
    from GarenaAI.db import get_connection
    from GarenaAI.memory_repository import MemoryRepository

_EXCLUDED_KEYS = {"event_type", "timestamp", "match_id", "user_id"}


class GameEventRepository:
    def __init__(self, memory: MemoryRepository | None = None) -> None:
        self._memory = memory or MemoryRepository()

    def summarize_events(self, events: Sequence[Mapping[str, Any]]) -> str:
        lines = [_summarize_event(event) for event in events]
        return "\n".join(line for line in lines if line) or "No events recorded."

    def ensure_user(self, display_name: str) -> UUID:
        return self._memory.ensure_user(display_name)

    def find_similar(
        self,
        user_id: UUID,
        game_id: UUID,
        embedding: Sequence[float],
        limit: int = 5,
    ) -> list[str]:
        """Return flattened event summaries for this player's most similar past recaps."""
        conn = get_connection()
        try:
            register_vector(conn)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT events
                        FROM user_game_data
                        WHERE user_id = %s AND game_id = %s
                        ORDER BY game_data <=> %s
                        LIMIT %s
                        """,
                        (user_id, game_id, Vector(embedding), limit),
                    )
                    return [self.summarize_events(row["events"]) for row in cur.fetchall()]
        finally:
            conn.close()

    def save_recap(
        self,
        user_id: UUID,
        game_id: UUID,
        events: Sequence[Mapping[str, Any]],
        embedding: Sequence[float],
    ) -> UUID:
        conn = get_connection()
        try:
            register_vector(conn)
            with conn:
                with conn.cursor() as cur:
                    row_id = uuid.uuid4()
                    cur.execute(
                        """
                        INSERT INTO user_game_data (id, user_id, game_id, events, game_data)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (row_id, user_id, game_id, Jsonb(list(events)), Vector(embedding)),
                    )
            return row_id
        finally:
            conn.close()


def _summarize_event(event: Mapping[str, Any]) -> str:
    event_type = str(event.get("event_type", "unknown_event"))
    parts: list[str] = []
    for key, value in event.items():
        if key in _EXCLUDED_KEYS or value is None:
            continue
        if key == "position" and isinstance(value, Mapping):
            continue  # raw coordinates aren't meaningful for semantic similarity
        if isinstance(value, Mapping):
            nested = ", ".join(f"{k}={v}" for k, v in value.items() if v is not None and k != "position")
            if nested:
                parts.append(f"{key}=({nested})")
            continue
        parts.append(f"{key}={value}")

    detail = ", ".join(parts)
    return f"{event_type}: {detail}" if detail else event_type
