"""Precapture the scripted demo arc into app/cache/*.json (B4).

On the OFFICE laptop (with Azure), run LIVE to capture real Azure responses:
    uv run python scripts/precache.py            # LIVE capture (needs Azure)
On THIS machine (no Azure), exercise the full path with synthesized FAKE
responses to prove the mechanism + populate a fixture cache for the test:
    uv run python scripts/precache.py --dry-run  # FAKE synth, no Azure

For each scripted turn (hero -> follow-up A -> follow-up B -> presentation-change)
it runs the real pipeline (retrieve embeds, validate + execute against the seeded
DB run for real) and captures every LLM interaction (embed + generate + summarize)
under the frozen cache-key scheme sha256(canonical-json(messages))[:16], preserving
conversation history so history-dependent keys match on replay.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm.base import LLMClient, LLMMode, Message  # noqa: E402
from app.llm.cached_client import CACHE_DIR, _key  # noqa: E402
from app.llm import fake_responses as fr  # noqa: E402
from app.llm.fake_client import FakeLLMClient  # noqa: E402
from app.llm.prompts import GENERATE_SYSTEM, SUMMARIZE_SYSTEM  # noqa: E402
from app.metadata import demo_questions  # noqa: E402
from app.pipeline.run import run_question  # noqa: E402
from app.session.store import session_store  # noqa: E402
from app.config import settings  # noqa: E402

CONV_ID = "demo"  # stable conversation id so history-dependent cache keys are reproducible


def _extract_question(messages: list[Message]) -> str:
    m = re.search(r"Question:\s*(.+)", messages[-1]["content"])
    return m.group(1).splitlines()[0].strip() if m else ""


class CapturingClient(LLMClient):
    """Wraps LIVE (real capture) or synthesizes FAKE responses (dry-run), and
    writes every embed/chat interaction to the cache under the frozen key scheme,
    so CACHED mode replays them. It does NOT override generate_sql/summarize, so
    the base implementations build the exact messages CACHED will look up."""

    mode = LLMMode.LIVE

    def __init__(self, dry_run: bool, cache_dir: Path):
        self.dry_run = dry_run
        self.cache_dir = cache_dir
        self.fake = FakeLLMClient()
        self.live = None
        if not dry_run:
            from app.llm.live_client import LiveLLMClient

            self.live = LiveLLMClient()  # fails loud without Azure creds — by design
        self.written: list[tuple[str, str, str]] = []

    def _write(self, kind: str, payload: object, response: object) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        key = _key(kind, payload)
        path = self.cache_dir / f"{kind}_{key}.json"
        path.write_text(json.dumps({"response": response}, ensure_ascii=False), encoding="utf-8")
        self.written.append((kind, key, path.name))

    def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = self.fake.embed(texts) if self.dry_run else self.live.embed(texts)
        self._write("embed", texts, vecs)
        return vecs

    def chat(self, messages: list[Message], **kwargs) -> str:
        response = self._synthesize(messages) if self.dry_run else self.live.chat(messages, **kwargs)
        self._write("chat", messages, response)
        return response

    def _synthesize(self, messages: list[Message]) -> str:
        """Dry-run only: produce a response in the real Azure FORMAT (```sql fence
        / strict JSON) using FAKE logic, so CACHED's base parsers accept it."""
        system = messages[0]["content"]
        q = _extract_question(messages)
        key = fr.detect_demo_key(q)
        if SUMMARIZE_SYSTEM.split("\n", 1)[0] in system:  # summarize call
            if isinstance(key, str) and key in fr._DEMO:
                d = fr.demo_payload(key)
                return json.dumps({"summary": d["summary"], "chart": d["chart"]})
            return json.dumps({"summary": "Here are the results below.", "chart": {"type": "none"}})
        # generate call
        if isinstance(key, str) and key in fr._DEMO:
            sql = fr.demo_payload(key)["sql"]
        else:
            sql = fr.safe_extra_sql(q) or fr.heuristic_sql(q) or "SELECT 1"
        return f"```sql\n{sql}\n```"


async def run_precache(dry_run: bool, cache_dir: Path = CACHE_DIR) -> dict[str, Any]:
    dq = demo_questions()
    client = CapturingClient(dry_run=dry_run, cache_dir=cache_dir)

    async def _noop(_e):  # emit sink
        return None

    results: list[tuple[str, bool, object]] = []

    # 1) Scripted multi-turn hero arc (one conversation) + presentation change.
    hero_arc = list(dq.get("hero_arc", []))
    arc_seq = hero_arc + list(dq.get("presentation_changes", []))
    session_store.clear(CONV_ID)  # fresh history so keys rebuild identically on replay
    for q in arc_seq:
        r = await run_question(q, CONV_ID, client, settings.DEMO_SPONSOR, _noop)
        results.append((f"[arc] {q}", r.fast_path, r.error))

    # 2) Each remaining standalone wow question, captured fresh (no history).
    standalone = [e["question"] for e in dq.get("scripted", []) if e["question"] not in hero_arc]
    for i, q in enumerate(standalone):
        conv = f"{CONV_ID}_w{i}"
        session_store.clear(conv)
        r = await run_question(q, conv, client, settings.DEMO_SPONSOR, _noop)
        results.append((q, r.fast_path, r.error))

    return {"sequence": arc_seq + standalone, "results": results, "written": client.written}


def _print_summary(summary: dict[str, Any], dry_run: bool) -> None:
    print(f"\nPrecache {'DRY-RUN (FAKE synth, no Azure)' if dry_run else 'LIVE (real Azure)'}")
    print(f"Scripted turns: {len(summary['sequence'])}")
    for q, fast, err in summary["results"]:
        tag = "fast-path (no capture)" if fast else ("DECLINED" if err else "captured")
        print(f"  · {tag:>22} | {q}")
    print(f"\nCache files written: {len(summary['written'])}")
    for kind, key, name in summary["written"]:
        print(f"    {kind:>6}  {key}  -> {name}")
    misses = [q for q, fast, err in summary["results"] if err]
    print(f"Misses/errors: {len(misses)}")


def main() -> int:
    dry_run = "--dry-run" in sys.argv or settings.LLM_MODE.upper() != "LIVE"
    summary = asyncio.run(run_precache(dry_run=dry_run))
    _print_summary(summary, dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Re-export for clarity in tests.
__all__ = ["run_precache", "CapturingClient", "CONV_ID"]
