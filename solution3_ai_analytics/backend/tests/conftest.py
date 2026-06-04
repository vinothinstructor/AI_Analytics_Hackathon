"""Shared pytest fixtures. All tests run in FAKE mode (no Azure) against the
seeded local Postgres (docker compose up + seed must have run)."""
from __future__ import annotations

import pytest

from app.db.engine import engine, readonly_engine
from app.llm import build_client, LLMMode


@pytest.fixture(autouse=True)
async def _dispose_engine_pools():
    """pytest-asyncio gives each test its own event loop; the async engine pools
    cache connections bound to a loop. Dispose them after each test so the next
    test's loop gets fresh connections (avoids 'Event loop is closed')."""
    yield
    await engine.dispose()
    await readonly_engine.dispose()

HERO_Q = (
    "Which of my MOON-2026 sites are at risk of missing enrollment targets, "
    "and what's the 60-day trend?"
)


@pytest.fixture
def fake_client():
    return build_client(LLMMode.FAKE)


@pytest.fixture
def collector():
    """Returns (emit, events) — emit appends each SSE event to events."""
    events: list[dict] = []

    async def emit(event: dict) -> None:
        events.append(event)

    return emit, events
