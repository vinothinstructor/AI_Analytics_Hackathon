"""Debug routes. The Phase 2 graph needs runtime deps (LLM client, DB), so this
endpoint just confirms the graph compiled and reports its node names rather than
invoking it with a dummy state. Use POST /chat to exercise the real pipeline."""
from __future__ import annotations

from fastapi import APIRouter

from ..pipeline import COMPILED_GRAPH

router = APIRouter(prefix="/debug")


@router.get("/graph")
def graph_info() -> dict:
    nodes = [n for n in COMPILED_GRAPH.get_graph().nodes if n not in ("__start__", "__end__")]
    return {"compiled": True, "nodes": nodes}
