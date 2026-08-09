import os

from openai import AsyncOpenAI
from dotenv import load_dotenv
from fish_audio_sdk import Session, TTSRequest

try:
    from config import ENV_PATH, config_bool, config_float, config_int, config_value
except ImportError:
    from GarenaAI.config import ENV_PATH, config_bool, config_float, config_int, config_value

load_dotenv(ENV_PATH)
FISH_CLIENT = os.getenv("FISH_AUDIO_API_KEY")
session = Session(FISH_CLIENT) if FISH_CLIENT else None

FISH_TTS_API_CHARACTER_LIMIT = 500

async def speech_to_text(client: AsyncOpenAI, audio_bytes: bytes, filename: str = 'input.wav'):
    """converts user audio into text"""
    if not audio_bytes:
        return ""
    
    transcription = await client.audio.transcriptions.create(
        model = config_value("OPENAI_TRANSCRIBE_MODEL", "gpt-transcribe"),
        file = (filename, audio_bytes, "audio/wav")
    )

    return (transcription.text or "").strip()

def clamp_tts_text(text: str) -> str:
    """Return text that is safe for Fish TTS' character limit."""
    normalized = " ".join((text or "").split())
    if len(normalized) <= FISH_TTS_API_CHARACTER_LIMIT:
        return normalized

    clipped = normalized[:FISH_TTS_API_CHARACTER_LIMIT].rstrip()
    boundary = max(clipped.rfind("."), clipped.rfind("!"), clipped.rfind("?"))
    if boundary >= int(FISH_TTS_API_CHARACTER_LIMIT * 0.6):
        return clipped[: boundary + 1].strip()

    word_boundary = clipped.rfind(" ")
    if word_boundary >= int(FISH_TTS_API_CHARACTER_LIMIT * 0.8):
        return clipped[:word_boundary].strip()

    return clipped


def text_to_speech(text: str):
    """converts text into audio"""
    if session is None:
        return b""

    tts_text = clamp_tts_text(text)
    if not tts_text:
        return b""

    request = TTSRequest(
        text = tts_text,
        format = config_value("FISH_TTS_FORMAT", "mp3"),
        sample_rate = config_int("FISH_TTS_SAMPLE_RATE", 44100),
        mp3_bitrate = config_int("FISH_TTS_MP3_BITRATE", 128),
        latency = config_value("FISH_TTS_LATENCY", "balanced"),
        chunk_length = config_int("FISH_TTS_CHUNK_LENGTH", 200),
        normalize = config_bool("FISH_TTS_NORMALIZE", True),
        reference_id = _optional_config_value("FISH_TTS_REFERENCE_ID"),
        temperature = _sampling_config_value("FISH_TTS_TEMPERATURE", 0.2),
        top_p = _sampling_config_value("FISH_TTS_TOP_P", 0.5),
    )
    backend = config_value("FISH_TTS_BACKEND", "s2-pro")

    audio_bytes = b""

    for chunk in session.tts(request, backend=backend):
        audio_bytes += chunk

    return audio_bytes


def _optional_config_value(key: str) -> str | None:
    value = config_value(key).strip()
    return value or None


def _sampling_config_value(key: str, default: float) -> float:
    return max(0.0, min(config_float(key, default), 1.0))


def text_to_speech_mime_type():
    """returns the MIME type matching the configured Fish TTS output format"""
    output_format = config_value("FISH_TTS_FORMAT", "mp3").lower()
    if output_format == "wav":
        return "audio/wav"
    if output_format == "pcm":
        return "audio/pcm"
    return "audio/mpeg"
