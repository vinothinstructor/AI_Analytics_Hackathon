"""SSE /chat endpoint + /audit lookup.

Event protocol (named SSE events, JSON data): stage, sql, token, chart,
followups, trust, error, done.
  stage -> {"stage": "...", "status": "running"|"done", "detail"?: "<real fact>"}
    (Phase 5a: `detail` is an optional real fact per step — table/example counts,
     the injected-filter fact, real row count + latency — used by the UI's visible
     agent-reasoning sequence. Backward-compatible: detail is optional.)
  trust -> {"checks": {access_validated, tenant_injected, read_only, audit_logged},
            "audit": {query_id, latency_ms, rows_returned, tables_used}}
    (Phase 4: checks are data-driven from the real pipeline outcome.)
GET /audit/{query_id} -> {query_id, conversation_id, sponsor_id, sql, tables_used,
                          latency_ms, rows_returned, created_at}
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from ..config import settings
from ..db.app_models import QueryAudit
from ..db.engine import SessionLocal
from ..llm import LLMClient, resolve_llm_mode
from ..pipeline.run import run_question

router = APIRouter()


class ChatRequest(BaseModel):
    conversation_id: str
    question: str


def _sse(event: dict[str, Any]) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event.get('data', {}), default=str)}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest, client: LLMClient = Depends(resolve_llm_mode)):
    tenant = settings.DEMO_SPONSOR
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict[str, Any]) -> None:
        await queue.put(event)

    async def runner() -> None:
        try:
            await run_question(req.question, req.conversation_id, client, tenant, emit)
        except Exception as exc:  # noqa: BLE001 — surface as a graceful error event
            await queue.put({"event": "error", "data": {"message": f"Internal error: {exc}"}})
            await queue.put({"event": "done", "data": {}})
        finally:
            await queue.put(None)  # sentinel

    async def event_stream():
        task = asyncio.create_task(runner())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield _sse(event)
        finally:
            await task

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/audit/{query_id}")
async def get_audit(query_id: str):
    async with SessionLocal() as session:
        row = (
            await session.execute(select(QueryAudit).where(QueryAudit.query_id == query_id))
        ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No audit row for {query_id}")
    return {
        "query_id": row.query_id, "conversation_id": row.conversation_id,
        "sponsor_id": row.sponsor_id, "sql": row.sql,
        "tables_used": [t for t in (row.tables_used or "").split(",") if t],
        "latency_ms": row.latency_ms, "rows_returned": row.rows_returned,
        "created_at": row.created_at.isoformat(),
    }
