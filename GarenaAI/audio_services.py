import os

from openai import AsyncOpenAI
from dotenv import load_dotenv
from fish_audio_sdk import Session, TTSRequest

try:
    from config import ENV_PATH, config_int, config_value
except ImportError:
    from GarenaAI.config import ENV_PATH, config_int, config_value

load_dotenv(ENV_PATH)
FISH_CLIENT = os.getenv("FISH_AUDIO_API_KEY")
session = Session(FISH_CLIENT) if FISH_CLIENT else None 

async def speech_to_text(client: AsyncOpenAI, audio_bytes: bytes, filename: str = 'input.wav'):
    """converts user audio into text"""
    if not audio_bytes:
        return ""
    
    transcription = await client.audio.transcriptions.create(
        model = config_value("OPENAI_TRANSCRIBE_MODEL", "gpt-transcribe"),
        file = (filename, audio_bytes, "audio/wav")
    )

    return (transcription.text or "").strip()

def text_to_speech(text: str):
    """converts text into audio"""
    if session is None:
        return b""

    request = TTSRequest(
        text = text,
        model = config_value("FISH_TTS_MODEL", "s2.1-pro"),
        format = config_value("FISH_TTS_FORMAT", "mp3"),
        sample_rate = config_int("FISH_TTS_SAMPLE_RATE", 44100),
        mp3_bitrate = config_int("FISH_TTS_MP3_BITRATE", 128)
    )

    audio_bytes = b""

    for chunk in session.tts(request):
        audio_bytes += chunk

    return audio_bytes
