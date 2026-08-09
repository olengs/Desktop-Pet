import os
from pathlib import Path

from openai import AsyncOpenAI
from dotenv import load_dotenv
from fish_audio_sdk import Session, TTSRequest

load_dotenv(Path(__file__).with_name(".env"))
FISH_CLIENT = os.getenv("FISH_AUDIO_API_KEY")
session = Session(FISH_CLIENT) if FISH_CLIENT else None 
FISH_TTS_SAMPLE_RATE = 44100
FISH_TTS_MP3_BITRATE = 128

async def speech_to_text(client: AsyncOpenAI, audio_bytes: bytes, filename: str = 'input.wav'):
    """converts user audio into text"""
    if not audio_bytes:
        return ""
    
    transcription = await client.audio.transcriptions.create(
        model = "gpt-transcribe",
        file = (filename, audio_bytes, "audio/wav")
    )

    return (transcription.text or "").strip()

def text_to_speech(text: str):
    """converts text into audio"""
    if session is None:
        return b""

    request = TTSRequest(
        text = text,
        model = "s2.1-pro",
        format = "mp3",
        sample_rate = FISH_TTS_SAMPLE_RATE,
        mp3_bitrate = FISH_TTS_MP3_BITRATE
    )

    audio_bytes = b""

    for chunk in session.tts(request):
        audio_bytes += chunk

    return audio_bytes
