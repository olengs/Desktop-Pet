from __future__ import annotations

import logging
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
- Address the user's question directly and keep responses clear and concise, in under 3 sentences and under 500 characters so it fits nicely inside a desktop chat bubble and spoken reply.
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

DEATH_RECAP_SYSTEM_PROMPT = """
You are Mimo, a friendly, observant AI desktop pet companion for a gamer, reacting to a match death recap sent by the game.

*CURRENT DEATH RECAP*
{current_summary}

*SIMILAR PAST DEATHS FOR THIS PLAYER*
{similar_context}

*RULES*
- Only use facts present in the current recap or the similar past deaths above. Do not invent stats, positions, or causes not shown there.
- If similar past deaths show a repeating pattern (same weapon, same zone mistake, same habit), call it out directly.
- If there is no similar past death history, just react to the current recap.
- Be friendly, slightly playful, observant, and direct like a real gaming buddy giving quick feedback.
- Keep the reply under 3 sentences and under 500 characters so it fits a desktop chat bubble.
- Finish with a complete sentence. Prefer a shorter complete answer over a longer answer that trails off.
- Return only the reply, with no extra labels, preamble, or explanation.
"""

load_dotenv(ENV_PATH)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)

def empty_player_context(user_id: str) -> str:
    return f"""
    Display name: {user_id}
    Recent chat history: none yet.
    """

async def generate_response(user_id: str, user_message: str, player_context_text: str | None = None):
    prompt_context = player_context_text or empty_player_context(user_id)
    formatted_prompt = PET_SYSTEM_PROMPT.format(memory_context=prompt_context)
    # logger.info(
    #     "Formatted assistant prompt for player_id=%s system_chars=%d user_chars=%d\n"
    #     "--- SYSTEM PROMPT ---\n%s\n"
    #     "--- USER MESSAGE ---\n%s\n"
    #     "--- END ASSISTANT PROMPT ---",
    #     user_id,
    #     len(formatted_prompt),
    #     len(user_message),
    #     formatted_prompt,
    #     user_message,
    # )

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
        # logger.info(
        #     "Formatted memory summary prompt input turns=%d chars=%d\n"
        #     "--- SUMMARY SYSTEM PROMPT ---\n%s\n"
        #     "--- SUMMARY USER INPUT ---\n%s\n"
        #     "--- END SUMMARY PROMPT ---",
        #     len(chat_messages),
        #     len(summary_input),
        #     MEMORY_SUMMARY_PROMPT,
        #     summary_input,
        # )
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


async def embed_text(text: str) -> list[float]:
    """Embed a piece of text for pgvector similarity search."""
    response = await client.embeddings.create(
        model=config_value("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        input=text,
    )
    return response.data[0].embedding


async def generate_death_recap_feedback(
    user_id: str,
    current_summary: str,
    similar_summaries: Sequence[str],
) -> str:
    """React to a death recap, grounded in this player's similar past deaths."""
    similar_context = _format_similar_context(similar_summaries)
    formatted_prompt = DEATH_RECAP_SYSTEM_PROMPT.format(
        current_summary=current_summary,
        similar_context=similar_context,
    )

    try:
        llm_reply = await client.responses.create(
            model=config_value("OPENAI_RESPONSE_MODEL", "gpt-5.6-luna"),
            input=[{"role": "system", "content": formatted_prompt}],
            reasoning={"effort": config_value("OPENAI_REASONING_EFFORT", "medium")},
            max_output_tokens=config_int("OPENAI_MAX_OUTPUT_TOKENS", 240),
        )
    except Exception as e:
        print(e)
        return "Rough one out there. I couldn't pull up the full recap breakdown just now, but I've got it logged."

    reply = (llm_reply.output_text or "").strip()
    return reply or "Rough one out there. Try me again in a bit for the full breakdown."


def _format_similar_context(similar_summaries: Sequence[str]) -> str:
    if not similar_summaries:
        return "No similar past deaths on record yet."

    rows = [f"- {summary}" for summary in similar_summaries if summary]
    return "\n".join(rows) or "No similar past deaths on record yet."


if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_response("demo-player", "How are you?"))
