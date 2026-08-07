import base64
import traceback
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_engine import generate_response
from audio_services import text_to_speech

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

async def process_response(user_id, user_message):
    text_reply = await generate_response(
        user_id = user_id,
        user_message = user_message
    )

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
    try:
        result = await process_response(
            user_id = request.user_id,
            user_message = request.user_message
        )

        return ChatResponse(
            user_id = request.user_id,
            reply = result["reply"],
            audio_base64 = result["audio_base64"]
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{str(e)}")

#TO BE IMPLEMENTED
@app.post("/voice-chat")
async def voice_chat_endpoint(user_id = Form(...), audio_file = File(...)):
    return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
