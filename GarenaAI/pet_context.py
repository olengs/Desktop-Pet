from __future__ import annotations

from typing import Iterable, Protocol


class TraitScoresLike(Protocol):
    teamwork: int
    aggression: int
    loyalty: int
    leadership: int
    risk_taking: int


def format_player_context(
    player_id: str,
    memory_context: Iterable[str],
    traits: TraitScoresLike | None,
) -> str:
    """Format desktop-provided context for the existing AI prompt."""
    memories = [memory.strip() for memory in memory_context if memory and memory.strip()]
    lines = [f"Player ID: {player_id or 'demo-player'}"]

    trait_values = _trait_values(traits)
    if any(score != 0 for _, score in trait_values):
        trait_text = ", ".join(f"{name} {score:+d}" for name, score in trait_values)
        lines.append(f"Trait snapshot from desktop session: {trait_text}")
    else:
        lines.append("Trait snapshot from desktop session: no trait changes yet.")

    if memories:
        lines.append("Memories from desktop session:")
        lines.extend(f"- {memory}" for memory in memories)
    else:
        lines.append("Memories from desktop session: no match memories provided yet.")

    return "\n".join(lines)


def mood_from_traits(traits: TraitScoresLike | None) -> str:
    if traits is None:
        return "thinking"

    if traits.teamwork <= -2 or traits.loyalty <= -2:
        return "annoyed"

    support_signal = traits.teamwork + traits.loyalty + traits.leadership
    aggressive_signal = traits.aggression + traits.risk_taking
    if support_signal >= aggressive_signal + 2:
        return "happy"

    return "thinking"


def _trait_values(traits: TraitScoresLike | None) -> list[tuple[str, int]]:
    if traits is None:
        return [
            ("teamwork", 0),
            ("aggression", 0),
            ("loyalty", 0),
            ("leadership", 0),
            ("risk-taking", 0),
        ]

    return [
        ("teamwork", traits.teamwork),
        ("aggression", traits.aggression),
        ("loyalty", traits.loyalty),
        ("leadership", traits.leadership),
        ("risk-taking", traits.risk_taking),
    ]

