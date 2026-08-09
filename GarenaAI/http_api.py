from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

try:
    from ai_engine import embed_text, generate_death_recap_feedback
    from game_event_repository import GameEventRepository
except ImportError:  # Allows `python -m GarenaAI.http_api` from repo root.
    from GarenaAI.ai_engine import embed_text, generate_death_recap_feedback
    from GarenaAI.game_event_repository import GameEventRepository

logger = logging.getLogger(__name__)

app = FastAPI(title="Garena AI Telemetry")
_repo = GameEventRepository()


class DeathRecapRequest(BaseModel):
    user_id: str
    game_id: str
    events: list[dict[str, Any]]


class DeathRecapResponse(BaseModel):
    feedback: str
    similar_recaps_used: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/death-recap", response_model=DeathRecapResponse)
async def report_death_recap(payload: DeathRecapRequest) -> DeathRecapResponse:
    event_summary = _repo.summarize_events(payload.events)
    game_id = payload.game_id

    user_id = None
    try:
        user_id = await asyncio.to_thread(_repo.ensure_user, payload.user_id)
    except Exception:
        logger.exception("death recap identity resolution failed for user_id=%s", payload.user_id)

    embedding: list[float] | None = None
    try:
        embedding = await embed_text(event_summary)
    except Exception:
        logger.exception("death recap embedding failed for user_id=%s", payload.user_id)

    similar_summaries: list[str] = []
    if embedding is not None and user_id is not None:
        try:
            similar_summaries = await asyncio.to_thread(_repo.find_similar, user_id, game_id, embedding)
        except Exception:
            logger.exception("death recap similarity lookup failed for user_id=%s", payload.user_id)

    feedback = await generate_death_recap_feedback(payload.user_id, event_summary, similar_summaries)

    if embedding is not None and user_id is not None:
        try:
            await asyncio.to_thread(_repo.save_recap, user_id, game_id, payload.events, embedding)
        except Exception:
            logger.exception("death recap save failed for user_id=%s", payload.user_id)

    return DeathRecapResponse(
        feedback=feedback,
        similar_recaps_used=len(similar_summaries),
    )
