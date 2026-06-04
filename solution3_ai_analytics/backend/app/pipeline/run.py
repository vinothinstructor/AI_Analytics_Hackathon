"""Top-level orchestration: router + fast-path + full-pipeline run (B4/B5).

run_question() drives one turn, emitting the SSE event protocol via the async
`emit` callback and returning a Result (used directly by tests). The SSE endpoint
wraps emit with a queue; tests pass a list-appending emit.
"""
from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from ..llm.fake_responses import (
    GENERIC_DECLINE_MSG, OFF_DOMAIN_MSG, detect_presentation_change, is_in_domain,
)
from ..metadata import scripted_followups
from ..schemas import ChartSpec, Turn
from ..session.store import session_store
from .graph import COMPILED_GRAPH, ev

Emit = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class Result:
    summary: str = ""
    chart_spec: dict[str, Any] = field(default_factory=lambda: {"type": "none"})
    rows: list[dict[str, Any]] = field(default_factory=list)
    followups: list[str] = field(default_factory=list)
    sql_display: Optional[str] = None
    sql_final: Optional[str] = None
    query_id: Optional[str] = None
    tables_used: list[str] = field(default_factory=list)
    audit: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    fast_path: bool = False


def _new_query_id() -> str:
    return "q_" + secrets.token_hex(4)


def _chunk(text: str, words_per_chunk: int = 4) -> list[str]:
    words = text.split(" ")
    return [" ".join(words[i : i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]


def _history_dicts(conversation_id: str) -> list[dict[str, Any]]:
    state = session_store.get(conversation_id)
    return [
        {"question": t.question, "sql": t.sql, "result_digest": t.result_digest}
        for t in state.turns
    ]


def _result_digest(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "0 rows"
    cols = list(rows[0].keys())
    return f"{len(rows)} rows; columns: {cols}; sample: {rows[:2]}"


async def _emit_tokens(emit: Emit, summary: str) -> None:
    for piece in _chunk(summary):
        await emit(ev("token", text=piece + " "))
        await asyncio.sleep(0)  # let the SSE consumer flush


async def run_question(
    question: str, conversation_id: str, client, tenant: str, emit: Emit
) -> Result:
    # --- Router: pure presentation change -> fast path (no DB round-trip) ---
    chart_type = detect_presentation_change(question)
    if chart_type is not None:
        last = session_store.get_last_result(conversation_id)
        if not last:
            await emit(ev("token", text="Please ask a question first, then I can re-chart its result. "))
            await emit(ev("done"))
            return Result(summary="(no previous result to re-chart)", fast_path=True)
        new_spec = dict(last["chart_spec"])
        new_spec["type"] = chart_type
        summary = f"Here's the same data as a {chart_type if chart_type != 'none' else 'table'}."
        await _emit_tokens(emit, summary)
        await emit(ev("chart", chart_spec=new_spec, rows=last["rows"]))
        await emit(ev("done"))
        # Update the stored chart_spec so a subsequent re-chart chains correctly.
        session_store.set_last_result(conversation_id, last["rows"], new_spec)
        return Result(summary=summary, chart_spec=new_spec, rows=last["rows"], fast_path=True)

    # --- Relevance gate: clearly off-domain questions decline (no SQL) ---
    has_history = bool(session_store.get(conversation_id).turns)
    if not is_in_domain(question, has_history=has_history):
        await emit(ev("error", message=OFF_DOMAIN_MSG))
        await emit(ev("done"))
        return Result(error=OFF_DOMAIN_MSG)

    # --- Full pipeline (brand-new question OR refinement; history disambiguates) ---
    query_id = _new_query_id()
    state: dict[str, Any] = {
        "question": question, "conversation_id": conversation_id,
        "history": _history_dicts(conversation_id), "tenant": tenant,
        "client": client, "emit": emit, "query_id": query_id,
        "retries": 0, "stages_run": [],
    }
    final = await COMPILED_GRAPH.ainvoke(state)

    # Terminal failure: an explicit decline (unanswerable from schema) carries a
    # ready-to-show message; an exhausted-validation failure gets wrapped politely.
    if final.get("decline"):
        msg = final.get("error") or GENERIC_DECLINE_MSG
        await emit(ev("error", message=msg))
        await emit(ev("done"))
        return Result(error=msg)
    if not final.get("valid") or "rows" not in final:
        msg = final.get("error") or "I couldn't answer that against the available data."
        await emit(ev("error", message=_graceful(msg)))
        await emit(ev("done"))
        return Result(error=msg)

    rows = final.get("rows", [])
    summary = final.get("summary", "")
    chart_spec = _validate_chart(final.get("chart_spec", {"type": "none"}), rows)
    # Scripted demo questions always get their exact curated chips (so the arc is
    # identical in FAKE/CACHED/LIVE); otherwise use the model's / a heuristic set.
    followups = scripted_followups(question) or final.get("followups", []) or _heuristic_followups()

    await _emit_tokens(emit, summary)
    await emit(ev("chart", chart_spec=chart_spec, rows=rows))
    await emit(ev("followups", suggestions=followups))
    # Data-driven trust checks — each reflects the real pipeline outcome.
    checks = {
        "access_validated": bool(final.get("valid")),          # AST whitelist checks passed
        "tenant_injected": bool(final.get("tenant_injected")), # validator actually injected sponsor_id
        "read_only": True,                                     # executed via the app_readonly role
        "audit_logged": bool(final.get("audit")),              # an audit row was written
    }
    await emit(ev("trust", checks=checks, audit={
        "query_id": query_id, "latency_ms": final.get("latency_ms"),
        "rows_returned": len(rows), "tables_used": final.get("tables_used", []),
    }))
    await emit(ev("done"))

    # Persist turn + last result for memory and the fast-path.
    session_store.append_turn(conversation_id, Turn(
        question=question, sql=final.get("sql_final"),
        chart_spec=ChartSpec(**_coerce_chart(chart_spec)),
        result_digest=_result_digest(rows),
    ))
    session_store.set_last_result(conversation_id, rows, chart_spec)

    return Result(
        summary=summary, chart_spec=chart_spec, rows=rows, followups=followups,
        sql_display=final.get("sql_display"), sql_final=final.get("sql_final"),
        query_id=query_id, tables_used=final.get("tables_used", []), audit=final.get("audit"),
    )


def _validate_chart(spec: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """If the chart's x/y fields aren't real result columns, fall back to table."""
    spec = dict(spec or {"type": "none"})
    if spec.get("type", "none") == "none" or not rows:
        return spec
    cols = set(rows[0].keys())
    needed = [spec.get("x_field"), spec.get("y_field")]
    if any(f and f not in cols for f in needed):
        return {"type": "none", "title": spec.get("title", "Results")}
    return spec


def _coerce_chart(spec: dict[str, Any]) -> dict[str, Any]:
    allowed = {"type", "x_field", "y_field", "color_field", "title"}
    out = {k: v for k, v in spec.items() if k in allowed}
    if out.get("type") not in {"bar", "line", "pie", "donut", "scatter", "area", "none"}:
        out["type"] = "none"
    return out


def _heuristic_followups() -> list[str]:
    return ["Show this as a bar chart", "Break this down by country"]


def _graceful(reason: str) -> str:
    return (
        "I wasn't able to answer that with the data I have. "
        f"({reason}) Try rephrasing, or ask about studies, sites, patients, "
        "enrollment, visits, deviations, or user engagement."
    )
