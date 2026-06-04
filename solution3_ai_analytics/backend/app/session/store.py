"""In-memory conversation store (B5).

Keeps only the last few turns per conversation — enough for short-window memory
and the presentation fast-path Phase 2 will build. No persistence. Not yet wired
into the pipeline; this is the structure Phase 2 fills in.
"""
from __future__ import annotations

from ..schemas import ConversationState, Turn

MAX_TURNS = 3


class SessionStore:
    def __init__(self, max_turns: int = MAX_TURNS):
        self._max_turns = max_turns
        self._conversations: dict[str, ConversationState] = {}
        # Last full result per conversation — kept out of ConversationState (which
        # holds only digests) so the presentation fast-path can re-render rows
        # without a DB round-trip.
        self._last_result: dict[str, dict] = {}

    def get(self, conversation_id: str) -> ConversationState:
        state = self._conversations.get(conversation_id)
        if state is None:
            state = ConversationState(conversation_id=conversation_id)
            self._conversations[conversation_id] = state
        return state

    def append_turn(self, conversation_id: str, turn: Turn) -> ConversationState:
        state = self.get(conversation_id)
        state.turns.append(turn)
        # Cap to the last N turns.
        if len(state.turns) > self._max_turns:
            state.turns = state.turns[-self._max_turns :]
        return state

    def clear(self, conversation_id: str | None = None) -> None:
        """Reset one conversation (or all) — used by precache/replay so history
        rebuilds identically."""
        if conversation_id is None:
            self._conversations.clear()
            self._last_result.clear()
        else:
            self._conversations.pop(conversation_id, None)
            self._last_result.pop(conversation_id, None)

    def set_last_result(self, conversation_id: str, rows: list[dict], chart_spec: dict) -> None:
        self._last_result[conversation_id] = {"rows": rows, "chart_spec": chart_spec}

    def get_last_result(self, conversation_id: str) -> dict | None:
        return self._last_result.get(conversation_id)


# Process-wide singleton (sufficient for the single-process Phase 1 skeleton).
session_store = SessionStore()
