import base64
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_engine import generate_response, client
from audio_services import text_to_speech, speech_to_text

app = FastAPI(title="MVP Chat")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class ChatRequest(BaseModel):
    user_id: str
    user_message: str

class ChatResponse(BaseModel):
    user_id: str
    reply: str
    audio_base64: str

class VoiceChatResponse(BaseModel):
    user_id: str
    user_transcript: str
    reply: str
    audio_base64: str

async def process_response(user_id: str, user_message: str):
    """generate reply text and synthesize audio"""
    text_reply = await generate_response(user_id, user_message)

    if not text_reply or not text_reply.strip():
        text_reply = "I didn't quite catch that. Could you repeat it?"

    audio_bytes = text_to_speech(text_reply)
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    return {
        "reply": text_reply,
        "audio_base64": audio_b64
    }

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """handle chat between user and pet, returns text with voiceover"""
    try:
        result = await process_response(request.user_id, request.user_message)

        return ChatResponse(
            user_id = request.user_id,
            reply = result["reply"],
            audio_base64 = result["audio_base64"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")

#TO BE IMPLEMENTED
@app.post("/voice-chat")
async def voice_chat_endpoint(user_id: str = Form(...), audio_file: UploadFile = File(...)):
    """user's option to talk to the pet instead of type"""
    try:
        user_audio_bytes = await audio_file.read()

        user_transcript = await speech_to_text(client, user_audio_bytes, audio_file.filename)

        result = await process_response(user_id, user_transcript)

        return VoiceChatResponse(
            user_id = user_id,
            user_transcript = user_transcript,
            reply = result["reply"],
            audio_base64 = result["audio_base64"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
