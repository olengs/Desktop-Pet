import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from fish_audio_sdk import Session, TTSRequest

load_dotenv()
FISH_CLIENT = os.getenv("FISH_AUDIO_API_KEY")
session = Session(FISH_CLIENT) if FISH_CLIENT else None 

#async def speech_to_text():
#    transcription = await AsyncOpenAI.audio.transcription.create(
#        model = "whisper-1",
#        file = ("user_input.wav", bytes, "audio/wav")
#    )
#    return transcription.text.strip()

def text_to_speech(text):

    request = TTSRequest(
        text = text,
        model = "s2.1-pro",
        format = "mp3"
    )

    audio_bytes = b""

    for chunk in session.tts(request):
        audio_bytes += chunk

    return audio_bytes