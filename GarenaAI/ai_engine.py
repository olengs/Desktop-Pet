from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

PET_SYSTEM_PROMPT = """
You are a friendly, persistent, and observant AI desktop pet companion for a gamer.

Your job is to help the player understand their gameplay behaviour.

*PLAYER IDENTITY & MEMORIES*
{memory_context}

*PERSONALITY & RULES*
- Only draw conclusions supported by the provided player traits and memories. If relevant to the user's message, reference the provided game events or strong traits.
- Do not fake new game events and never pretend you remember something that is not provided. Only reference events explicitly provided in the memory context above.
- If the user's question requires context that is not provided here, do not guess; say so briefly and answer only from the available traits and memories.
- Be friendly, slightly playful, observant and direct like a real gaming buddy, providing practical observation when appropriate.
- Only compare behaviour across games when memories from multiple games support it, and do not treat one event as a permanent behaviour pattern.
- Address the user's question directly and keep responses clear and concise, in under 3 sentences max so it fits nicely inside a desktop chat bubble.
- Return only the reply to the user, with no extra labels, preamble, or explanation.
- Before finalizing, quickly check that every claim is grounded in the provided traits or memories and that the response stays within the sentence limit.
"""

load_dotenv(Path(__file__).with_name(".env"))
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#TEMPORARY
def mock_player_context(user_id: str):
    return """
    Traits: High aggression (85/100), Low teamwork (30/100)
    Memories:
    - rushed enemy lines alone in Free Fire and got eliminated early.
    - ignored team retreat ping in Arena of Valor.
    """
#TEMPORARY

async def generate_response(user_id: str, user_message: str, memory_context: str | None = None):
    prompt_context = memory_context or mock_player_context(user_id) #TO BE REPLACED (brod)
    formatted_prompt = PET_SYSTEM_PROMPT.format(memory_context=prompt_context)

    try: 
        llm_reply = await client.responses.create(
            model = "gpt-5.6-luna", #to decide which gpt model
            input = [
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_message}
            ],
            reasoning={"effort":"medium"},
            max_output_tokens = 120
        )
    except Exception as e:
        print(e)
        return "broke"
    
    response = llm_reply.output_text
    return response

if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_response("demo-player", "How am I playing?"))
