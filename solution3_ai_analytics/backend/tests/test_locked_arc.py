"""Locked-arc guard: the hero question, through the real FAKE-mode pipeline,
must reproduce the exact MOON-2026 percentages and ranking. Fails loudly if the
data or the hero response ever drifts."""
import pytest

from app.pipeline.run import run_question
from tests.conftest import HERO_Q


@pytest.mark.asyncio
async def test_hero_arc_locked(fake_client, collector):
    emit, events = collector
    r = await run_question(HERO_Q, "test_arc", fake_client, "helix_therapeutics", emit)

    assert len(r.rows) == 14, "MOON-2026 has 14 sites"
    by = {row["name"]: row["pct_of_target"] for row in r.rows}
    assert by["Munich"] == 82
    assert by["São Paulo"] == 67
    assert by["Tokyo"] == 45
    assert by["Boston"] == 38
    assert by["Toronto"] == 28

    # Tokyo / Boston / Toronto are the three lowest, unambiguously ordered.
    ordered = sorted(r.rows, key=lambda x: x["pct_of_target"])
    assert [row["name"] for row in ordered[:3]] == ["Toronto", "Boston", "Tokyo"]
    assert all(row["pct_of_target"] > 45 for row in ordered[3:])

    # The hand-authored hero summary names all three at-risk sites.
    for name in ("Toronto", "Tokyo", "Boston"):
        assert name in r.summary

    # SSE contract sanity: five stages present, a chart with bar type.
    done = [e["data"] for e in events if e["event"] == "stage" and e["data"]["status"] == "done"]
    assert [d["stage"] for d in done] == ["retrieve", "generate", "validate", "execute", "summarize"]
    assert r.chart_spec["type"] == "bar"

    # Phase 5a: stage detail lines carry REAL values.
    detail = {d["stage"]: d.get("detail", "") for d in done}
    assert "8 relevant tables" in detail["retrieve"]
    assert "Tenant filter injected" in detail["validate"]
    assert detail["execute"].startswith("14 rows · ")
