"""FAKE mode — the local-dev mode on the personal MacBook (no Azure).

Hand-authored deterministic responses keyed to known demo inputs, with a
heuristic fallback for unknown inputs. Embeddings use deterministic
pseudo-vectors (see pseudo.py). Nothing here touches Azure.

Phase 1 keeps the keyed table intentionally small — it exists to prove the
plumbing and answer /llm/ping. The real NL2SQL keyed responses arrive in
Phase 2 once the pipeline nodes call chat() for actual work.
"""
from __future__ import annotations

from typing import Any

from . import fake_responses as fr
from .base import DeclineRequest, LLMClient, LLMMode, Message
from .pseudo import pseudo_embed

# Keyed responses: substring match against the last user message (lower-cased).
# Phase 2 grows this with real SQL-generation and summarization fixtures.
_KEYED: list[tuple[str, str]] = [
    ("ping", "pong"),
]


def _keyed_lookup(text: str) -> str | None:
    needle = text.lower()
    for key, response in _KEYED:
        if key in needle:
            return response
    return None


class FakeLLMClient(LLMClient):
    mode = LLMMode.FAKE

    def chat(self, messages: list[Message], **kwargs) -> str:
        last = messages[-1]["content"] if messages else ""
        keyed = _keyed_lookup(last)
        if keyed is not None:
            return keyed
        # Heuristic fallback for unknown inputs: deterministic, clearly labelled.
        return f"[FAKE] no keyed fixture for input; echoing: {last!r}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [pseudo_embed(t) for t in texts]

    # Hand-authored demo responses + heuristic fallback (see fake_responses.py).
    def generate_sql(self, question, context, history=None, error=None) -> str:  # noqa: ARG002
        key = fr.detect_demo_key(question, history)
        if isinstance(key, tuple) and key[0] == "refine":
            return fr.refine_sql(key[1])
        if key in fr._DEMO:
            return fr.demo_payload(key)["sql"]
        # Curated safe-extras: return the prepared aggregate/filter SQL so FAKE
        # rehearsal answers them respectably (real data -> clean table).
        extra = fr.safe_extra_sql(question)
        if extra:
            return extra
        # Decline rather than dump SELECT *: a requested field that doesn't exist,
        # or a question that maps to no table, is answered gracefully upstream.
        decline = fr.answerability_decline(question)
        if decline:
            raise DeclineRequest(decline)
        sql = fr.heuristic_sql(question)
        if sql is None:
            raise DeclineRequest(fr.GENERIC_DECLINE_MSG)
        return sql

    def summarize(self, question, sql, rows, history=None) -> dict[str, Any]:  # noqa: ARG002
        key = fr.detect_demo_key(question, history)
        if isinstance(key, str) and key in fr._DEMO:
            return dict(fr.demo_payload(key))  # summary + chart + followups
        if isinstance(key, tuple) and key[0] == "refine":
            site = key[1]
            pct = rows[0].get("pct_of_target") if rows else None
            summary = (
                f"{site} has {rows[0].get('enrolled')} enrolled patients "
                f"({pct}% of its target of {rows[0].get('target_enrollment')})."
                if rows else f"No enrollment data found for {site}."
            )
            return {
                "summary": summary,
                "chart": {"type": "bar", "x_field": "name", "y_field": "pct_of_target",
                          "color_field": None, "title": f"{site} enrollment vs target"},
                "followups": ["Compare that to Munich", "Show the 60-day trend"],
            }
        return fr.heuristic_summary(question, rows, sql)
