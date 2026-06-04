"""The scripted wow set renders the right chart type from real executed data
(FAKE provides the SQL; the SQL runs for real, so numbers are genuine)."""
import pytest

from app.pipeline.run import run_question

HELIX = "helix_therapeutics"


async def _noop(_e):
    return None


async def _ask(client, q, conv):
    return await run_question(q, conv, client, HELIX, _noop)


@pytest.mark.asyncio
async def test_wow_set_chart_types_and_data(fake_client):
    cases = {
        "deviations": ("Where are my protocol deviations concentrated across MOON-2026 sites?", "bar"),
        "scatter": ("How do site size and screen-failure rate relate for MOON-2026?", "scatter"),
        "cumulative": ("Show cumulative enrollment over the past year for MOON-2026.", "area"),
        "severity": ("Break down protocol deviations by severity.", "donut"),
        "visit": ("What's the visit completion mix for MOON-2026?", "pie"),
        "screenfail_site": ("Show screen-failure rates across my MOON-2026 sites.", "bar"),
        "trend": ("Show the 60-day enrollment trend for the at-risk sites.", "line"),
    }
    out = {}
    for key, (q, _t) in cases.items():
        out[key] = await _ask(fake_client, q, f"wow_{key}")

    # Chart types are the intended striking ones.
    for key, (_q, t) in cases.items():
        assert out[key].chart_spec["type"] == t, f"{key} should be {t}"

    # Data is real and matches the probe.
    dev = {r["name"]: r["deviations"] for r in out["deviations"].rows}
    assert dev["Tokyo"] == 40 and dev["Toronto"] == 37 and dev["Boston"] == 27

    assert len(out["scatter"].rows) == 14
    assert {"enrolled", "screen_fail_pct", "status"} <= set(out["scatter"].rows[0])

    assert out["cumulative"].rows[-1]["cumulative"] == 831

    sev = {r["severity"]: r["n"] for r in out["severity"].rows}
    assert (sev["minor"], sev["major"], sev["critical"]) == (126, 51, 23)

    vis = {r["status"]: r["n"] for r in out["visit"].rows}
    assert vis["completed"] > vis["scheduled"] > vis["missed"]

    sf = {r["name"]: r["screen_fail_pct"] for r in out["screenfail_site"].rows}
    assert sf["Toronto"] == 32.1 and sf["Tokyo"] == 28.9 and sf["Boston"] == 28.9

    # Multi-line trend includes the healthy reference (Munich) + the at-risk sites.
    names = {r["name"] for r in out["trend"].rows}
    assert "Munich" in names and {"Tokyo", "Boston", "Toronto"} & names
