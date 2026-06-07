"""Health + LLM-mode round-trip routes (B3). No /api prefix (Vite proxy strips it)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import settings
from ..llm import LLMClient, resolve_llm_mode

router = APIRouter()


@router.get("/health")
def health() -> dict:
    # `llm_mode` is the server default (from .env); the frontend uses it to seed
    # the mode dropdown so the header reflects the configured mode.
    return {"status": "ok", "service": "solution3", "port": 8003, "llm_mode": settings.LLM_MODE}


@router.get("/llm/ping")
def llm_ping(client: LLMClient = Depends(resolve_llm_mode)) -> dict:
    """Proves header-based mode routing end to end. Does a trivial chat
    round-trip through whichever client the X-LLM-Mode header resolved to.

    In LIVE with no Azure creds, resolving the client raises before we get here
    and the app's exception handler returns a readable 500 (fail-loud), NOT a
    silent success.
    """
    reply = client.chat([{"role": "user", "content": "ping"}])
    return {"mode": client.mode.value, "reply": reply}
