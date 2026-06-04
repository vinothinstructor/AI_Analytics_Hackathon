"""LLM abstraction layer.

Every LLM call in Solution 3 routes through `LLMClient`. Four implementations
(MOCK / FAKE / CACHED / LIVE) are selected per-request by the X-LLM-Mode header
(see resolve.py). This is the contract they all honor.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

Message = dict[str, str]  # {"role": "user"|"system"|"assistant", "content": ...}

EMBED_DIM = 1536  # text-embedding-3-small


class DeclineRequest(Exception):
    """Raised by a client's generate_sql when a question cannot be answered from
    the schema (e.g. a field that doesn't exist). The pipeline turns this into a
    graceful `error` event instead of executing a fallback query."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LLMMode(str, Enum):
    MOCK = "MOCK"      # template/skeleton responses; no LLM, no embeddings
    FAKE = "FAKE"      # hand-authored deterministic responses + heuristic fallback
    CACHED = "CACHED"  # replays previously-captured real LIVE responses
    LIVE = "LIVE"      # real-time Azure OpenAI calls

    @classmethod
    def parse(cls, raw: str | None, default: "LLMMode") -> "LLMMode":
        if not raw:
            return default
        try:
            return cls(raw.strip().upper())
        except ValueError:
            return default


class LLMClient(ABC):
    """Common interface for all four modes."""

    mode: LLMMode

    @abstractmethod
    def chat(self, messages: list[Message], **kwargs) -> str:
        """Return a completion string for the given chat messages."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one EMBED_DIM-length vector per input text."""

    # ---- High-level pipeline operations --------------------------------------
    # Default implementations build prompts and call chat(); LIVE and CACHED use
    # these as-is. MOCK and FAKE override them (skeleton / hand-authored).

    def generate_sql(
        self,
        question: str,
        context: str,
        history: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> str:
        from .prompts import build_generate_messages, parse_sql

        reply = self.chat(build_generate_messages(question, context, history, error))
        return parse_sql(reply)

    def summarize(
        self,
        question: str,
        sql: str,
        rows: list[dict[str, Any]],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return {"summary": str, "chart": {...}, "followups"?: [...]}."""
        from .prompts import build_summarize_messages, parse_summary

        reply = self.chat(build_summarize_messages(question, sql, rows, history))
        return parse_summary(reply)
