"""CACHED mode — replays previously-captured real LIVE responses.

This is the demo-recording mode: the responses in app/cache/*.json are real
Azure output captured once on the office laptop (Phase 5), then replayed here
deterministically and instantly. Cached *is* real Azure data — that's the
integrity story for the Round 3 defense.

Phase 1 ships an empty cache dir. A cache miss raises a clear error rather than
falling back, so it's obvious when a fixture still needs to be captured.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import LLMClient, LLMMode, Message

# backend/app/cache  (this file is backend/app/llm/cached_client.py)
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


class CacheMissError(RuntimeError):
    """Raised when CACHED mode has no captured response for an input."""


def _key(kind: str, payload: object) -> str:
    blob = json.dumps({"kind": kind, "payload": payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class CachedLLMClient(LLMClient):
    mode = LLMMode.CACHED

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir

    def _load(self, kind: str, payload: object) -> object:
        path = self.cache_dir / f"{kind}_{_key(kind, payload)}.json"
        if not path.exists():
            raise CacheMissError(
                f"CACHED mode: no captured {kind} response at {path.name}. "
                f"Capture it in LIVE mode on the office laptop first (Phase 5)."
            )
        return json.loads(path.read_text(encoding="utf-8"))["response"]

    def chat(self, messages: list[Message], **kwargs) -> str:
        return self._load("chat", messages)  # type: ignore[return-value]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._load("embed", texts)  # type: ignore[return-value]
