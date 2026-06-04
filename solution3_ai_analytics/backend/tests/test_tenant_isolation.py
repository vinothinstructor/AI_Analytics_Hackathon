"""Tenant isolation: the auto-injected sponsor_id filter must keep tenants'
data fully separate. Proves the security claim against the seeded two-tenant DB."""
import pytest

from app.pipeline.run import run_question
from tests.conftest import HERO_Q

HELIX = "helix_therapeutics"
MERIDIAN = "meridian_pharmaceuticals"
MOON_SITES = {"Munich", "São Paulo", "Tokyo", "Boston", "Toronto"}


async def _noop(_event):  # emit sink
    return None


@pytest.mark.asyncio
async def test_helix_scoped_has_no_meridian_rows(fake_client):
    r = await run_question(HERO_Q, "ti_helix", fake_client, HELIX, _noop)
    # Rendered SQL carries the injected tenant predicate.
    assert ":sponsor_id" in (r.sql_final or "")
    assert "sponsor_id = :sponsor_id" in (r.sql_display or "")
    assert len(r.rows) == 14  # all MOON-2026 (Helix) sites, none from Meridian

    # A second, broad query (all sites) must return ONLY Helix rows.
    r2 = await run_question("show me all sites", "ti_helix2", fake_client, HELIX, _noop)
    assert r2.rows and all(row["sponsor_id"] == HELIX for row in r2.rows)
    assert any(row["name"] in MOON_SITES for row in r2.rows)


@pytest.mark.asyncio
async def test_meridian_scoped_has_no_helix_rows(fake_client):
    # The MOON-2026 hero query scoped to Meridian returns ZERO rows (MOON is Helix's).
    r = await run_question(HERO_Q, "ti_mer", fake_client, MERIDIAN, _noop)
    assert r.rows == []

    # All-sites scoped to Meridian: only Meridian sites, none of Helix's MOON cities.
    r2 = await run_question("show me all sites", "ti_mer2", fake_client, MERIDIAN, _noop)
    assert r2.rows and all(row["sponsor_id"] == MERIDIAN for row in r2.rows)
    names = {row["name"] for row in r2.rows}
    assert not (names & MOON_SITES)
    assert all(n.split(" ")[0] in {"HALO-2027", "VERTEX-2026", "COMET-2025"} for n in names)
