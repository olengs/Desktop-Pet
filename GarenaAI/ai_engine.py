from __future__ import annotations

import os
from typing import Mapping, Sequence

from dotenv import load_dotenv
from openai import AsyncOpenAI

try:
    from config import ENV_PATH, config_int, config_value
except ImportError:
    from GarenaAI.config import ENV_PATH, config_int, config_value

PET_SYSTEM_PROMPT = """
You are a friendly, persistent, and observant AI desktop pet companion for a gamer.

Your job is to be a conversational companion. You can chat about games, planning, focus, or whatever the user brings up, but you do not receive live game events from the desktop pet.

*PLAYER IDENTITY & CONVERSATION MEMORY*
{memory_context}

*PERSONALITY & RULES*
- Use the provided conversation summary and recent chat context when relevant.
- Do not pretend to know stored gameplay details, hidden stats, or events that are not in the provided conversation memory or current message.
- If the user's question requires unavailable context, say so briefly and answer from what they tell you in the conversation.
- Be friendly, slightly playful, observant, and direct like a real gaming buddy.
- Address the user's question directly and keep responses clear and concise, in under 3 sentences max so it fits nicely inside a desktop chat bubble.
- Finish with a complete sentence. Prefer a shorter complete answer over a longer answer that trails off.
- Return only the reply to the user, with no extra labels, preamble, or explanation.
- Before finalizing, quickly check that every claim is grounded in the recent chat context or the user's current message.
"""

MEMORY_SUMMARY_PROMPT = """
You maintain a rolling conversation memory for Mimo, a friendly desktop pet companion.

Create a new replacement summary by combining the existing summary with the new chat turns. Preserve stable user preferences, recurring goals, emotional context, names, plans, and useful facts that could help future replies. Remove filler, one-off greetings, and details that are unlikely to matter again.

Rules:
- Do not invent gameplay stats, hidden memories, or facts not present in the existing summary or new chat turns.
- Do not append the new turns after the old summary; merge them into one coherent updated summary.
- Keep the summary compact and readable.
- Prefer short bullets or tight sentences.
- Return only the updated summary.
"""

load_dotenv(ENV_PATH)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def empty_player_context(user_id: str) -> str:
    return f"""
    Display name: {user_id}
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


async def summarize_chat_memory(
    existing_summary: str,
    chat_messages: Sequence[Mapping[str, str]],
) -> str:
    """Fold a batch of chat messages into a replacement rolling summary."""
    if not chat_messages:
        return existing_summary.strip()

    summary_input = _format_summary_input(existing_summary, chat_messages)

    try:
        completion = await client.chat.completions.create(
            model=config_value("GARENA_MEMORY_SUMMARY_MODEL", config_value("OPENAI_RESPONSE_MODEL", "gpt-5.6-luna")),
            messages=[
                {"role": "system", "content": MEMORY_SUMMARY_PROMPT},
                {"role": "user", "content": summary_input},
            ],
            max_completion_tokens=config_int("GARENA_MEMORY_SUMMARY_MAX_OUTPUT_TOKENS", 360),
        )
    except Exception as e:
        print(e)
        return ""

    message = completion.choices[0].message
    return (message.content or "").strip()


def _format_summary_input(
    existing_summary: str,
    chat_messages: Sequence[Mapping[str, str]],
) -> str:
    existing = existing_summary.strip() or "No existing summary yet."
    rows = []
    for message in chat_messages:
        role = "Mimo" if message.get("role") == "assistant" else str(message.get("role", "user")).title()
        source = message.get("source", "text")
        content = " ".join(str(message.get("content", "")).split())
        if content:
            rows.append(f"- {role} ({source}): {content}")

    return "\n".join(
        [
            "Existing rolling summary:",
            existing,
            "",
            "New chat turns to fold in:",
            "\n".join(rows) or "- No new chat turns.",
        ]
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_response("demo-player", "How are you?"))
