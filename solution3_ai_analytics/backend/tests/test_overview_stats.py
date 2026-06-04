"""B3: read-only overview stats are real and tenant-scoped to Helix."""
import pytest

from app.routers.overview import overview_stats


@pytest.mark.asyncio
async def test_overview_stats_real_and_scoped():
    data = await overview_stats()
    assert data["active_studies"] == 5          # Helix's 5 active studies
    assert data["total_sites"] == 80            # Helix sites only (Meridian's 24 excluded)
    assert data["enrolled_patients"] == 5000    # Helix patients only
    assert data["at_risk_sites"] == 3           # Tokyo / Boston / Toronto < 50%
    codes = {s["code"] for s in data["studies"]}
    assert "MOON-2026" in codes
    # Tenant isolation: no Meridian study leaks in.
    assert not (codes & {"HALO-2027", "VERTEX-2026", "COMET-2025"})
