"""B5: the recorded demo arc replays deterministically in CACHED mode, and a
cache miss fails loudly (so a missing capture surfaces during rehearsal, not on
camera). Uses a fixture cache produced by the precache dry-run into a tmp dir."""
import pytest

from app.llm.cached_client import CachedLLMClient, CacheMissError
from app.metadata import demo_questions
from app.pipeline.run import run_question
from app.session.store import session_store
from scripts.precache import CONV_ID, run_precache

HELIX = "helix_therapeutics"
HERO, FOLLOW_A, FOLLOW_B = demo_questions()["hero_arc"]  # exact captured arc


async def _noop(_e):
    return None


async def _replay(client, question, conv=CONV_ID):
    return await run_question(question, conv, client, HELIX, _noop)


@pytest.mark.asyncio
async def test_recorded_arc_replays_deterministically(tmp_path):
    # Populate a fixture cache via the dry-run capture (FAKE synth, no Azure).
    await run_precache(dry_run=True, cache_dir=tmp_path)
    cached = CachedLLMClient(cache_dir=tmp_path)

    async def play_sequence():
        session_store.clear(CONV_ID)  # fresh history so keys rebuild identically
        hero = await _replay(cached, HERO)
        a = await _replay(cached, FOLLOW_A)
        b = await _replay(cached, FOLLOW_B)
        pie = await _replay(cached, "show me as a pie chart")
        return hero, a, b, pie

    hero, a, b, pie = await play_sequence()

    # Hero arc replayed from cache, executed for real -> locked numbers.
    by = {r["name"]: r["pct_of_target"] for r in hero.rows}
    assert len(hero.rows) == 14
    assert (by["Munich"], by["São Paulo"], by["Tokyo"], by["Boston"], by["Toronto"]) == (82, 67, 45, 38, 28)
    for name in ("Toronto", "Tokyo", "Boston"):
        assert name in hero.summary
    assert hero.chart_spec["type"] == "bar"
    assert a.chart_spec["type"] == "line"   # follow-up A (60-day trend)
    assert b.chart_spec["type"] == "bar"    # follow-up B (Tokyo screen-failure)
    assert pie.fast_path and pie.chart_spec["type"] == "pie"  # presentation fast-path

    # Determinism: same inputs -> identical outputs.
    hero2, a2, b2, _ = await play_sequence()
    assert hero2.rows == hero.rows
    assert hero2.summary == hero.summary
    assert a2.summary == a.summary and b2.summary == b.summary


@pytest.mark.asyncio
async def test_cache_miss_fails_loud(tmp_path):
    await run_precache(dry_run=True, cache_dir=tmp_path)
    cached = CachedLLMClient(cache_dir=tmp_path)
    session_store.clear("miss_conv")
    # A question never captured -> a clean, readable cache-miss error (not silent).
    with pytest.raises(CacheMissError):
        await _replay(cached, "How many investigators are assigned per study?", conv="miss_conv")
