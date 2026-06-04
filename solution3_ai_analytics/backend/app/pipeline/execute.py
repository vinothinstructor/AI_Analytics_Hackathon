"""execute-stage helpers: read-only execution + audit write.

Execution goes through the SELECT-only app_readonly connection with a 5s
statement timeout and a 1000-row cap. The audit row is written with the
privileged connection (app_readonly cannot write).
"""
from __future__ import annotations

import datetime as dt
import time
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from ..db.app_models import QueryAudit
from ..db.engine import ReadOnlySessionLocal, SessionLocal

MAX_ROWS = 1000
STATEMENT_TIMEOUT_MS = 5000


def _jsonify(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


def _row_to_dict(mapping) -> dict[str, Any]:
    return {k: _jsonify(v) for k, v in mapping.items()}


async def run_readonly(sql_final: str, sponsor: str) -> tuple[list[dict[str, Any]], int]:
    params = {"sponsor_id": sponsor} if ":sponsor_id" in sql_final else {}
    async with ReadOnlySessionLocal() as session:
        async with session.begin():
            await session.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
            t0 = time.perf_counter()
            result = await session.execute(text(sql_final), params)
            rows = [_row_to_dict(r._mapping) for r in result.fetchmany(MAX_ROWS)]
            latency_ms = int((time.perf_counter() - t0) * 1000)
    return rows, latency_ms


async def write_audit(
    query_id: str, conversation_id: str, sponsor: str, sql_final: str,
    latency_ms: int, rows_returned: int, tables_used: list[str] | None = None,
) -> dict[str, Any]:
    created_at = dt.datetime.now(dt.timezone.utc)
    tables = tables_used or []
    async with SessionLocal() as session:
        session.add(QueryAudit(
            query_id=query_id, conversation_id=conversation_id, sponsor_id=sponsor,
            sql=sql_final, tables_used=",".join(tables), latency_ms=latency_ms,
            rows_returned=rows_returned, created_at=created_at,
        ))
        await session.commit()
    return {
        "query_id": query_id, "conversation_id": conversation_id, "sponsor_id": sponsor,
        "sql": sql_final, "tables_used": tables, "latency_ms": latency_ms,
        "rows_returned": rows_returned, "created_at": created_at.isoformat(),
    }
