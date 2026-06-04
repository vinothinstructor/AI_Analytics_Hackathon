"""Presentation fast-path: given a prior turn, 'show me as a pie chart' re-renders
the same rows with a new chart type WITHOUT new SQL / a new audit row."""
import pytest
from sqlalchemy import func, select

from app.db.app_models import QueryAudit
from app.db.engine import SessionLocal
from app.pipeline.run import run_question
from tests.conftest import HERO_Q


async def _noop(_event):
    return None


async def _audit_count() -> int:
    async with SessionLocal() as s:
        return (await s.execute(select(func.count()).select_from(QueryAudit))).scalar_one()


@pytest.mark.asyncio
async def test_pie_fastpath_no_new_query(fake_client, collector):
    conv = "fastpath_conv"
    # Prior turn establishes a last result + one audit row.
    first = await run_question(HERO_Q, conv, fake_client, "helix_therapeutics", _noop)
    assert first.query_id is not None
    before = await _audit_count()

    emit, events = collector
    r = await run_question("show me as a pie chart", conv, fake_client, "helix_therapeutics", emit)

    assert r.fast_path is True
    assert r.query_id is None
    assert r.chart_spec["type"] == "pie"
    assert r.rows == first.rows  # same data, re-charted

    # No pipeline events and no new audit row.
    event_types = {e["event"] for e in events}
    assert "stage" not in event_types
    assert "sql" not in event_types
    assert {"token", "chart", "done"} <= event_types
    assert await _audit_count() == before
