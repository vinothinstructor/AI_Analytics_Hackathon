"""Per-request LLM-mode resolution.

`resolve_llm_mode` is a FastAPI dependency: it reads the X-LLM-Mode header,
falls back to the server default (settings.LLM_MODE), and returns the matching
client. Mid-session mode switching works without a restart because the client
is chosen fresh on every request.

LIVE construction can raise (fail-loud on missing Azure creds); we let that
propagate so the route surfaces a clear HTTP 500 rather than a silent fallback.
"""
from __future__ import annotations

from fastapi import Header

from ..config import settings
from .base import LLMClient, LLMMode
from .cached_client import CachedLLMClient
from .fake_client import FakeLLMClient
from .live_client import LiveLLMClient
from .mock_client import MockLLMClient


def build_client(mode: LLMMode) -> LLMClient:
    if mode is LLMMode.MOCK:
        return MockLLMClient()
    if mode is LLMMode.FAKE:
        return FakeLLMClient()
    if mode is LLMMode.CACHED:
        return CachedLLMClient()
    if mode is LLMMode.LIVE:
        return LiveLLMClient()  # may raise AzureCredentialsMissingError — by design
    raise ValueError(f"Unhandled LLM mode: {mode}")


def resolve_llm_mode(
    x_llm_mode: str | None = Header(default=None, alias="X-LLM-Mode"),
) -> LLMClient:
    default = LLMMode.parse(settings.LLM_MODE, LLMMode.FAKE)
    mode = LLMMode.parse(x_llm_mode, default)
    return build_client(mode)
