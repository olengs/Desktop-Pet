from __future__ import annotations

import asyncio
import io
import logging
import os
from pathlib import Path
import struct
import time
import uuid
import wave
from collections import defaultdict
from dataclasses import dataclass

import grpc

try:
    from config import config_bool, config_float, config_value
    from ai_engine import client, generate_response
    from audio_services import speech_to_text, text_to_speech, text_to_speech_mime_type
    from generated import garena_pet_pb2 as pb
    from generated import garena_pet_pb2_grpc as rpc
    from memory_repository import MemoryRepository, MemorySettings
except ImportError:  # Allows `python -m GarenaAI.main` from repo root.
    from GarenaAI.config import config_bool, config_float, config_value
    from GarenaAI.ai_engine import client, generate_response
    from GarenaAI.audio_services import speech_to_text, text_to_speech, text_to_speech_mime_type
    from GarenaAI.generated import garena_pet_pb2 as pb
    from GarenaAI.generated import garena_pet_pb2_grpc as rpc
    from GarenaAI.memory_repository import MemoryRepository, MemorySettings

logger = logging.getLogger(__name__)

DEFAULT_PLAYER_ID = "demo-player"
DEFAULT_WAV_DIR = Path(__file__).resolve().parent.parent / "test"
DEFAULT_MOOD = "thinking"
STT_SAMPLE_RATE = 16000


@dataclass(frozen=True)
class GrpcServiceConfig:
    enable_tts: bool = config_bool("GARENA_PET_GRPC_TTS", False)
    save_wav: bool = config_bool("GARENA_PET_SAVE_WAV", False)
    save_tts_wav: bool = config_bool("GARENA_PET_SAVE_TTS_WAV", False)
    wav_dir: Path = Path(config_value("GARENA_PET_WAV_DIR", "") or DEFAULT_WAV_DIR)
    stream_heartbeat_seconds: float = config_float("GARENA_PET_GRPC_HEARTBEAT_SECONDS", 30)
    memory: MemorySettings = MemorySettings.from_config()


class PlayerMessageHub:
    def __init__(self) -> None:
        self._pending: dict[str, list[pb.PetServerMessage]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue[pb.PetServerMessage]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, player_id: str, message: pb.PetServerMessage) -> None:
        async with self._lock:
            pending = self._pending[player_id]
            pending.append(message)
            del pending[:-50]
            subscribers = list(self._subscribers[player_id])

        for subscriber in subscribers:
            try:
                subscriber.put_nowait(message)
            except asyncio.QueueFull:
                logger.debug("dropping queued pet message for slow subscriber")

    async def pull(self, player_id: str, max_messages: int, after_message_id: str = "") -> list[pb.PetServerMessage]:
        limit = min(max(max_messages or 10, 1), 50)

        async with self._lock:
            pending = self._pending[player_id]
            if after_message_id:
                start = next(
                    (index + 1 for index, message in enumerate(pending) if message.message_id == after_message_id),
                    0,
                )
                return list(pending[start : start + limit])

            messages = list(pending[:limit])
            del pending[:limit]
            return messages

    async def register(self, player_id: str) -> asyncio.Queue[pb.PetServerMessage]:
        queue: asyncio.Queue[pb.PetServerMessage] = asyncio.Queue(maxsize=20)
        async with self._lock:
            self._subscribers[player_id].add(queue)
        return queue

    async def unregister(self, player_id: str, queue: asyncio.Queue[pb.PetServerMessage]) -> None:
        async with self._lock:
            self._subscribers[player_id].discard(queue)


class GarenaPetGrpcService(rpc.GarenaPetServiceServicer):
    def __init__(
        self,
        hub: PlayerMessageHub | None = None,
        config: GrpcServiceConfig | None = None,
        memory_repository: MemoryRepository | None = None,
    ) -> None:
        self._hub = hub or PlayerMessageHub()
        self._config = config or GrpcServiceConfig()
        self._memory = memory_repository or MemoryRepository(self._config.memory)

    async def SendText(self, request: pb.TextRequest, context: grpc.aio.ServicerContext) -> pb.PetResponse:
        player_id = _player_id(request.player_id)
        message = request.message.strip()
        if not message:
            return pb.PetResponse(
                request_id=request.request_id,
                reply="Say that again for me. I need a little text to work with.",
                mood="thinking",
            )

        reply = await self._generate_reply(player_id, message)
        await self._remember_chat_turn(
            player_id,
            request.request_id,
            user_message=message,
            assistant_reply=reply,
            source="text",
        )
        mood = DEFAULT_MOOD
        return await self._pet_response(request.request_id, reply, mood)

    async def SendVoice(self, request: pb.VoiceRequest, context: grpc.aio.ServicerContext):
        player_id = _player_id(request.player_id)
        if not request.wav_audio:
            yield pb.PetResponse(
                request_id=request.request_id,
                reply="I did not receive any audio. Try one more quick voice note.",
                mood="thinking",
            )
            return

        wav_audio = _canonicalize_wav_for_stt(bytes(request.wav_audio))
        if self._config.save_wav:
            await asyncio.to_thread(
                _save_wav_debug_copy,
                self._config.wav_dir,
                player_id,
                request.request_id,
                wav_audio,
            )

        try:
            transcript = await speech_to_text(client, wav_audio, "desktop-pet.wav")
        except Exception:
            logger.exception("voice transcription failed")
            yield pb.PetResponse(
                request_id=request.request_id,
                reply="I could not transcribe that voice note yet. Type it to me while the speech backend wakes up.",
                mood="thinking",
            )
            return

        if not transcript:
            yield pb.PetResponse(
                request_id=request.request_id,
                transcript="",
                reply="I could not make out that voice note. Try again a little closer to the mic.",
                mood="thinking",
            )
            return

        yield pb.PetResponse(
            request_id=request.request_id,
            transcript=transcript,
            mood=DEFAULT_MOOD,
        )
        reply = await self._generate_reply(player_id, transcript)
        await self._remember_chat_turn(
            player_id,
            request.request_id,
            user_message=transcript,
            assistant_reply=reply,
            source="voice",
        )
        mood = DEFAULT_MOOD
        yield await self._pet_response(request.request_id, reply, mood)

    async def PullMessages(
        self,
        request: pb.PullMessagesRequest,
        context: grpc.aio.ServicerContext,
    ) -> pb.MessageBatch:
        player_id = _player_id(request.player_id)
        messages = await self._hub.pull(player_id, request.max_messages, request.after_message_id)
        return pb.MessageBatch(messages=messages)

    async def SubscribeMessages(self, request: pb.SubscribeRequest, context: grpc.aio.ServicerContext):
        player_id = _player_id(request.player_id)
        queue = await self._hub.register(player_id)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=self._config.stream_heartbeat_seconds,
                    )
                except asyncio.TimeoutError:
                    message = _text_server_message("Mimo receive stream is alive.", "idle")

                yield message
        finally:
            await self._hub.unregister(player_id, queue)

    async def _generate_reply(self, player_id: str, message: str) -> str:
        prompt_context = await self._build_prompt_context(player_id, message)
        reply = await generate_response(player_id, message, player_context_text=prompt_context)
        return _reply_or_fallback(reply)

    async def _build_prompt_context(self, player_id: str, message: str) -> str | None:
        db_context = await self._run_memory_op(
            "build prompt context",
            self._memory.build_prompt_context,
            player_id,
            message,
        )
        return db_context

    async def _remember_chat_turn(
        self,
        player_id: str,
        request_id: str,
        user_message: str,
        assistant_reply: str,
        source: str,
    ) -> None:
        await self._run_memory_op(
            "save user chat message",
            self._memory.save_chat_message,
            player_id,
            "user",
            user_message,
            source,
            request_id,
        )
        await self._run_memory_op(
            "save assistant chat message",
            self._memory.save_chat_message,
            player_id,
            "assistant",
            assistant_reply,
            source,
            request_id,
        )

    async def _run_memory_op(self, label: str, func, *args):
        if not self._config.memory.enabled:
            return None
        try:
            return await asyncio.to_thread(func, *args)
        except Exception:
            logger.exception("memory operation failed: %s", label)
            return None

    async def _pet_response(
        self,
        request_id: str,
        reply: str,
        mood: str,
        transcript: str = "",
    ) -> pb.PetResponse:
        response = pb.PetResponse(
            request_id=request_id,
            reply=reply,
            mood=mood or "thinking",
            transcript=transcript,
        )
        audio = await self._optional_audio_payload(request_id, reply, transcript)
        if audio is not None:
            response.audio.CopyFrom(audio)
        return response

    async def _optional_audio_payload(self, request_id: str, reply: str, transcript: str = "") -> pb.AudioPayload | None:
        if not self._config.enable_tts or not reply:
            return None

        try:
            logger.info("Generating TTS audio for %d response characters", len(reply))
            audio_bytes = await asyncio.to_thread(text_to_speech, reply)
        except Exception:
            logger.exception("text-to-speech synthesis failed")
            return None

        if not audio_bytes:
            logger.warning("TTS was enabled but no audio bytes were generated; check FISH_AUDIO_API_KEY and Fish settings")
            return None

        mime_type = text_to_speech_mime_type()
        if self._config.save_tts_wav:
            await asyncio.to_thread(
                _save_tts_debug_copy,
                self._config.wav_dir,
                request_id,
                audio_bytes,
                mime_type,
            )

        logger.info("Generated TTS audio payload: %d bytes, mime_type=%s", len(audio_bytes), mime_type)
        return pb.AudioPayload(
            audio=audio_bytes,
            mime_type=mime_type,
            transcript=transcript,
            text=reply,
        )


def _player_id(player_id: str) -> str:
    return player_id.strip() or DEFAULT_PLAYER_ID


def _reply_or_fallback(reply: str | None) -> str:
    if reply and reply.strip():
        return reply.strip()
    return "I heard you, but I need a little more context before I call the play."


def _canonicalize_wav_for_stt(wav_audio: bytes) -> bytes:
    try:
        with wave.open(io.BytesIO(wav_audio), "rb") as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            frame_count = reader.getnframes()
            compression = reader.getcomptype()
            frames = reader.readframes(frame_count)
    except (EOFError, wave.Error):
        logger.warning("received voice payload is not a readable WAV; forwarding original bytes")
        return wav_audio

    if compression != "NONE" or sample_width != 2 or channels <= 0 or sample_rate <= 0 or not frames:
        logger.warning(
            "received unsupported WAV format channels=%s sample_width=%s sample_rate=%s compression=%s; forwarding original bytes",
            channels,
            sample_width,
            sample_rate,
            compression,
        )
        return wav_audio

    sample_count = len(frames) // 2
    samples = struct.unpack(f"<{sample_count}h", frames[: sample_count * 2])
    mono_samples = _downmix_int16_to_mono(samples, channels)
    canonical_samples = _resample_int16_mono(mono_samples, sample_rate, STT_SAMPLE_RATE)

    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(STT_SAMPLE_RATE)
        writer.writeframes(struct.pack(f"<{len(canonical_samples)}h", *canonical_samples))

    return output.getvalue()


def _downmix_int16_to_mono(samples: tuple[int, ...], channels: int) -> list[int]:
    if channels == 1:
        return list(samples)

    frame_count = len(samples) // channels
    mono: list[int] = []
    mono_append = mono.append
    for frame in range(frame_count):
        start = frame * channels
        mono_append(_clamp_int16(round(sum(samples[start : start + channels]) / channels)))
    return mono


def _resample_int16_mono(samples: list[int], source_rate: int, target_rate: int) -> list[int]:
    if source_rate == target_rate or not samples:
        return samples

    target_count = max(1, round(len(samples) * target_rate / source_rate))
    output: list[int] = []
    output_append = output.append
    last_index = len(samples) - 1
    for frame in range(target_count):
        source_position = frame * source_rate / target_rate
        left_index = min(int(source_position), last_index)
        right_index = min(left_index + 1, last_index)
        fraction = source_position - left_index
        value = samples[left_index] + (samples[right_index] - samples[left_index]) * fraction
        output_append(_clamp_int16(round(value)))
    return output


def _clamp_int16(value: int) -> int:
    return max(-32768, min(32767, value))


def _save_wav_debug_copy(wav_dir: Path, player_id: str, request_id: str, wav_audio: bytes) -> Path:
    wav_dir.mkdir(parents=True, exist_ok=True)
    safe_player_id = _safe_filename_part(player_id)
    safe_request_id = _safe_filename_part(request_id or str(uuid.uuid4()))
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = wav_dir / f"{timestamp}-{safe_player_id}-{safe_request_id}.wav"
    path.write_bytes(wav_audio)
    logger.info("saved desktop pet WAV debug copy to %s", path)
    return path


def _save_tts_debug_copy(wav_dir: Path, request_id: str, audio_bytes: bytes, mime_type: str) -> Path:
    wav_dir.mkdir(parents=True, exist_ok=True)
    safe_request_id = _safe_filename_part(request_id or str(uuid.uuid4()))
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    extension = "wav" if "wav" in mime_type.lower() else "audio"
    path = wav_dir / f"{timestamp}-mimo-tts-{safe_request_id}.{extension}"
    path.write_bytes(audio_bytes)
    logger.info("saved Mimo TTS debug copy to %s", path)
    return path


def _safe_filename_part(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip())
    return safe.strip("-") or "unknown"


def _text_server_message(text: str, mood: str) -> pb.PetServerMessage:
    return pb.PetServerMessage(
        message_id=str(uuid.uuid4()),
        mood=mood or "thinking",
        created_at_unix_ms=int(time.time() * 1000),
        text=pb.TextPayload(text=text),
    )
