"""B0: trust checks are data-driven and the audit endpoint returns the full row."""
import pytest

from app.pipeline.execute import write_audit
from app.pipeline.run import run_question
from tests.conftest import HERO_Q

HELIX = "helix_therapeutics"


@pytest.mark.asyncio
async def test_trust_checks_data_driven(fake_client):
    events: list[dict] = []

    async def emit(e):
        events.append(e)

    await run_question(HERO_Q, "trust1", fake_client, HELIX, emit)
    trust = next(e["data"] for e in events if e["event"] == "trust")

    checks = trust["checks"]
    assert checks["tenant_injected"] is True   # validator really injected sponsor_id
    assert checks["access_validated"] is True
    assert checks["read_only"] is True
    assert checks["audit_logged"] is True
    assert trust["audit"]["rows_returned"] == 14
    assert "sites" in trust["audit"]["tables_used"]


@pytest.mark.asyncio
async def test_audit_endpoint_returns_sql_and_tables(fake_client):
    # Write an audit row directly, then read it back through the route handler.
    import uuid

    from app.routers.chat import get_audit

    qid = "q_" + uuid.uuid4().hex[:8]  # unique so reruns don't collide on the PK
    await write_audit(qid, "convX", HELIX, "SELECT 1 FROM app.sites s",
                      latency_ms=3, rows_returned=1, tables_used=["sites", "studies"])
    row = await get_audit(qid)
    assert row["query_id"] == qid
    assert row["sponsor_id"] == HELIX
    assert "SELECT" in row["sql"]
    assert row["tables_used"] == ["sites", "studies"]
    assert "created_at" in row
