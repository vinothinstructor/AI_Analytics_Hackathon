"""MOCK mode — template/skeleton responses. No LLM, no embeddings.

Pure dev plumbing: proves the routing works without producing anything
resembling a real answer.
"""
from __future__ import annotations

from typing import Any

from .base import EMBED_DIM, LLMClient, LLMMode, Message


class MockLLMClient(LLMClient):
    mode = LLMMode.MOCK

    def chat(self, messages: list[Message], **kwargs) -> str:
        last = messages[-1]["content"] if messages else ""
        return f"[MOCK] received {len(messages)} message(s); last={last!r}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Zero vectors — placeholders, never used for real retrieval.
        return [[0.0] * EMBED_DIM for _ in texts]

    # Skeleton plumbing — no real generation/summarization.
    def generate_sql(self, question, context, history=None, error=None) -> str:  # noqa: ARG002
        return "SELECT 1"

    def summarize(self, question, sql, rows, history=None) -> dict[str, Any]:  # noqa: ARG002
        return {"summary": "[mock summary]", "chart": {"type": "none", "title": "[mock]"},
                "followups": []}
