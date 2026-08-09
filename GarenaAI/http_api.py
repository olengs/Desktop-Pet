from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

try:
    from ai_engine import embed_text, generate_death_recap_feedback
    from audio_services import clamp_tts_text, text_to_speech, text_to_speech_mime_type
    from config import config_bool, config_value
    from game_event_repository import GameEventRepository
    from generated import garena_pet_pb2 as pb
except ImportError:  # Allows `python -m GarenaAI.http_api` from repo root.
    from GarenaAI.ai_engine import embed_text, generate_death_recap_feedback
    from GarenaAI.audio_services import clamp_tts_text, text_to_speech, text_to_speech_mime_type
    from GarenaAI.config import config_bool, config_value
    from GarenaAI.game_event_repository import GameEventRepository
    from GarenaAI.generated import garena_pet_pb2 as pb

logger = logging.getLogger(__name__)

app = FastAPI(title="Garena AI Telemetry")
_repo = GameEventRepository()
_message_hub: Any | None = None


def configure_message_delivery(message_hub: Any) -> None:
    global _message_hub
    _message_hub = message_hub


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

    await _publish_death_recap_feedback(payload.user_id, feedback)

    return DeathRecapResponse(
        feedback=feedback,
        similar_recaps_used=len(similar_summaries),
    )


async def _publish_death_recap_feedback(player_id: str, feedback: str) -> None:
    if _message_hub is None:
        logger.warning("death recap feedback generated but no desktop message hub is configured")
        return

    message = await _feedback_server_message(feedback)
    for target_player_id in _desktop_player_targets(player_id):
        await _message_hub.publish(target_player_id, message)


async def _feedback_server_message(feedback: str) -> pb.PetServerMessage:
    tts_text = clamp_tts_text(feedback)
    if config_bool("GARENA_PET_GRPC_TTS", False) and tts_text:
        try:
            audio_bytes = await asyncio.to_thread(text_to_speech, tts_text)
        except Exception:
            logger.exception("death recap TTS generation failed")
        else:
            if audio_bytes:
                return pb.PetServerMessage(
                    message_id=str(uuid.uuid4()),
                    mood="thinking",
                    created_at_unix_ms=int(time.time() * 1000),
                    audio=pb.AudioPayload(
                        audio=audio_bytes,
                        mime_type=text_to_speech_mime_type(),
                        text=tts_text,
                    ),
                )

    return pb.PetServerMessage(
        message_id=str(uuid.uuid4()),
        mood="thinking",
        created_at_unix_ms=int(time.time() * 1000),
        text=pb.TextPayload(text=feedback),
    )


def _desktop_player_targets(player_id: str) -> list[str]:
    targets = [player_id.strip()]
    configured_player_id = config_value("GARENA_DEATH_RECAP_PUSH_PLAYER_ID", "demo-player").strip()
    if configured_player_id:
        targets.append(configured_player_id)

    return list(dict.fromkeys(target for target in targets if target))
