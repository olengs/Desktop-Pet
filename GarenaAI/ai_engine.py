from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

try:
    from config import ENV_PATH, config_int, config_value
except ImportError:
    from GarenaAI.config import ENV_PATH, config_int, config_value

PET_SYSTEM_PROMPT = """
You are a friendly, persistent, and observant AI desktop pet companion for a gamer.

Your job is to be a conversational companion. You can chat about games, planning, focus, or whatever the user brings up, but you do not receive live game events from the desktop pet.

*PLAYER IDENTITY & RECENT CHAT CONTEXT*
{memory_context}

*PERSONALITY & RULES*
- Use the provided recent chat context when it is relevant.
- Do not pretend to know stored gameplay details, long-term memories, hidden stats, or events that are not in the recent chat context.
- If the user's question requires unavailable context, say so briefly and answer from what they tell you in the conversation.
- Be friendly, slightly playful, observant, and direct like a real gaming buddy.
- Address the user's question directly and keep responses clear and concise, in under 3 sentences max so it fits nicely inside a desktop chat bubble.
- Finish with a complete sentence. Prefer a shorter complete answer over a longer answer that trails off.
- Return only the reply to the user, with no extra labels, preamble, or explanation.
- Before finalizing, quickly check that every claim is grounded in the recent chat context or the user's current message.
"""

load_dotenv(ENV_PATH)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def empty_player_context(user_id: str) -> str:
    return f"""
    Player ID: {user_id}
    Recent chat history: none yet.
    """

async def generate_response(user_id: str, user_message: str, player_context_text: str | None = None):
    prompt_context = player_context_text or empty_player_context(user_id)
    formatted_prompt = PET_SYSTEM_PROMPT.format(memory_context=prompt_context)

    try: 
        llm_reply = await client.responses.create(
            model = config_value("OPENAI_RESPONSE_MODEL", "gpt-5.6-luna"),
            input = [
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_message}
            ],
            reasoning={"effort": config_value("OPENAI_REASONING_EFFORT", "medium")},
            max_output_tokens = config_int("OPENAI_MAX_OUTPUT_TOKENS", 240)
        )
    except Exception as e:
        print(e)
        return "broke"
    
    response = llm_reply.output_text
    return response

if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_response("demo-player", "How are you?"))
