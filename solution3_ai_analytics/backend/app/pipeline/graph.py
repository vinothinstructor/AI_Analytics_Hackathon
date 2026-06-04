"""LangGraph NL→SQL pipeline (Phase 2: real nodes).

Five nodes — retrieve / generate / validate / execute / summarize — wired
linearly with a retry edge from validate back to generate (max 2 retries).
Node names drive the UI stage chips in Phase 3.

In FAKE mode only the three LLM-dependent steps are stubbed (embed in retrieve,
generate, summarize via the FakeLLMClient); validate + execute run for real
against the seeded DB. Runtime objects (client, emit callback, tenant, query_id)
ride along in the state.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Callable, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..llm.base import DeclineRequest
from .execute import run_readonly, write_audit
from .retrieval import retrieve_context
from .validate import extract_tables, validate_and_inject

MAX_RETRIES = 2


def ev(name: str, **data: Any) -> dict[str, Any]:
    return {"event": name, "data": data}


class PipelineState(TypedDict, total=False):
    # Inputs / runtime
    question: str
    conversation_id: str
    history: list[dict[str, Any]]
    tenant: str
    client: Any            # LLMClient
    emit: Callable         # async event emitter
    query_id: str
    # Stage outputs
    retrieved_context: dict[str, Any]
    context_text: str
    sql: Optional[str]
    valid: bool
    sql_final: Optional[str]
    sql_display: Optional[str]
    tables_used: list[str]
    tenant_injected: bool
    rows: list[dict[str, Any]]
    latency_ms: int
    audit: dict[str, Any]
    summary: str
    chart_spec: dict[str, Any]
    followups: list[str]
    error: Optional[str]
    decline: bool
    retries: int
    stages_run: Annotated[list[str], operator.add]


async def _emit(state: PipelineState, event: dict[str, Any]) -> None:
    emit = state.get("emit")
    if emit is not None:
        await emit(event)


async def retrieve_node(state: PipelineState) -> dict[str, Any]:
    await _emit(state, ev("stage", stage="retrieve", status="running"))
    client = state["client"]
    qvec = client.embed([state["question"]])[0]
    ctx = await retrieve_context(qvec)
    detail = f"Found {len(ctx['tables'])} relevant tables · {len(ctx['examples'])} example queries"
    await _emit(state, ev("stage", stage="retrieve", status="done", detail=detail))
    return {"retrieved_context": ctx, "context_text": ctx["context_text"], "stages_run": ["retrieve"]}


async def generate_node(state: PipelineState) -> dict[str, Any]:
    await _emit(state, ev("stage", stage="generate", status="running"))
    client = state["client"]
    try:
        sql = client.generate_sql(
            state["question"], state.get("context_text", ""), state.get("history"),
            error=state.get("error"),
        )
    except DeclineRequest as d:
        # Cannot answer from the schema — decline gracefully (no fallback query).
        await _emit(state, ev("stage", stage="generate", status="done", detail="No matching schema field"))
        return {"decline": True, "error": d.message, "valid": False, "stages_run": ["generate"]}
    tables = extract_tables(sql)
    detail = f"Drafted SQL over {', '.join(tables)}" if tables else "Drafted candidate SQL"
    await _emit(state, ev("stage", stage="generate", status="done", detail=detail))
    return {"sql": sql, "stages_run": ["generate"]}


def _after_generate(state: PipelineState) -> str:
    return "terminal" if state.get("decline") else "validate"


async def validate_node(state: PipelineState) -> dict[str, Any]:
    await _emit(state, ev("stage", stage="validate", status="running"))
    result = validate_and_inject(state.get("sql") or "")
    out: dict[str, Any] = {"stages_run": ["validate"]}
    if result["ok"]:
        # Real injection flag: did the validator add the sponsor_id predicate?
        tenant_injected = ":sponsor_id" in (result["sql_final"] or "")
        out.update({
            "valid": True, "sql_final": result["sql_final"], "sql_display": result["sql_display"],
            "tables_used": result["tables_used"], "tenant_injected": tenant_injected, "error": None,
        })
        await _emit(state, ev("sql", sql_display=result["sql_display"],
                              query_id=state.get("query_id"), tenant_injected=tenant_injected))
        detail = "✓ Read-only · ✓ Tenant filter injected" if tenant_injected else "✓ Read-only"
    else:
        out.update({"valid": False, "error": result["error"], "retries": state.get("retries", 0) + 1})
        detail = "Validation failed — retrying"
    await _emit(state, ev("stage", stage="validate", status="done", detail=detail))
    return out


def _after_validate(state: PipelineState) -> str:
    if state.get("valid"):
        return "execute"
    if state.get("retries", 0) < MAX_RETRIES:
        return "generate"
    return "terminal"  # retries exhausted -> graceful error (skip execute/summarize)


async def execute_node(state: PipelineState) -> dict[str, Any]:
    await _emit(state, ev("stage", stage="execute", status="running"))
    rows, latency_ms = await run_readonly(state["sql_final"], state["tenant"])
    audit = await write_audit(
        state["query_id"], state["conversation_id"], state["tenant"],
        state["sql_final"], latency_ms, len(rows), state.get("tables_used", []),
    )
    await _emit(state, ev("stage", stage="execute", status="done",
                          detail=f"{len(rows)} rows · {latency_ms} ms"))
    return {"rows": rows, "latency_ms": latency_ms, "audit": audit, "stages_run": ["execute"]}


async def summarize_node(state: PipelineState) -> dict[str, Any]:
    await _emit(state, ev("stage", stage="summarize", status="running"))
    client = state["client"]
    out = client.summarize(state["question"], state["sql_final"], state["rows"], state.get("history"))
    await _emit(state, ev("stage", stage="summarize", status="done", detail="Building summary + chart"))
    return {
        "summary": out.get("summary", ""),
        "chart_spec": out.get("chart", {"type": "none"}),
        "followups": out.get("followups", []),
        "stages_run": ["summarize"],
    }


def build_graph() -> StateGraph:
    g = StateGraph(PipelineState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.add_node("validate", validate_node)
    g.add_node("execute", execute_node)
    g.add_node("summarize", summarize_node)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_conditional_edges(
        "generate", _after_generate, {"validate": "validate", "terminal": END},
    )
    g.add_conditional_edges(
        "validate", _after_validate,
        {"generate": "generate", "execute": "execute", "terminal": END},
    )
    g.add_edge("execute", "summarize")
    g.add_edge("summarize", END)
    return g


COMPILED_GRAPH = build_graph().compile()
