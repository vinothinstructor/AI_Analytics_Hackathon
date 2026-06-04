"""Graceful decline: questions that can't be answered from the schema (absent
field) or are off-domain must emit an `error` event — never a chart/table or a
raw SELECT * dump."""
import pytest

from app.pipeline.run import run_question

HELIX = "helix_therapeutics"


def _collector():
    events: list[dict] = []

    async def emit(e):
        events.append(e)

    return emit, events


@pytest.mark.asyncio
async def test_absent_field_declines(fake_client):
    emit, events = _collector()
    r = await run_question("What's the average age of the patients?", "dec_age", fake_client, HELIX, emit)

    types = [e["event"] for e in events]
    assert "error" in types
    assert "chart" not in types  # no chart/table answer
    assert r.error and "age" in r.error.lower()
    assert r.query_id is None  # nothing executed -> no audit row
    assert r.rows == []


@pytest.mark.asyncio
async def test_off_domain_declines(fake_client):
    emit, events = _collector()
    r = await run_question("What's the weather today?", "dec_weather", fake_client, HELIX, emit)

    types = [e["event"] for e in events]
    assert types == ["error", "done"]  # straight to a polite decline, no pipeline
    assert "chart" not in types
    assert r.error and "clinical trial" in r.error.lower()
    assert r.query_id is None


async def _noop(_e):
    return None


@pytest.mark.asyncio
async def test_in_domain_listing_still_answers(fake_client):
    # A legitimate in-domain question still answers (regression guard).
    r = await run_question("show me all sites", "dec_sites", fake_client, HELIX, _noop)
    assert r.error is None
    assert r.rows  # returned data, not a decline
