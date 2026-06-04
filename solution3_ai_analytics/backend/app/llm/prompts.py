"""Prompt construction + response parsing shared by the LLM clients.

The base LLMClient.generate_sql / summarize build messages here and call chat();
LIVE and CACHED use them as-is. MOCK and FAKE override the high-level methods.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .base import Message

GENERATE_SYSTEM = """You are a PostgreSQL expert for a clinical-trials analytics product.
Given a user question, the available tables, and example question→SQL pairs, write ONE PostgreSQL SELECT query.

Rules:
- Output ONLY the SQL, between ```sql fences. No prose.
- Use ONLY the tables provided in the context. Schema-qualify every table as app.<table>.
- Always alias tables (e.g. app.sites s) and qualify columns.
- Do NOT add any tenant/sponsor filter — the system injects sponsor_id automatically.
- Prefer JOINs over subqueries.
- Add LIMIT 100 unless the query is an aggregation (GROUP BY / single-row aggregate).
"""

SUMMARIZE_SYSTEM = """You summarize SQL query results for a clinical-trials dashboard.
Return STRICT JSON only (no prose, no fences) with this shape:
{"summary": "<2-3 sentence natural-language answer>",
 "chart": {"type": "bar|line|pie|scatter|area|none", "x_field": "<col>", "y_field": "<col>",
           "color_field": "<col or null>", "title": "<short title>"}}

Choose chart type by data shape: time series→line, categorical comparison→bar,
parts-of-whole→pie, two numeric columns→scatter, cumulative→area, otherwise→none (table).
x_field/y_field MUST be actual columns in the result. If nothing fits, use type "none".
"""


def _history_block(history: list[dict[str, Any]] | None) -> str:
    if not history:
        return ""
    lines = []
    for t in history[-3:]:
        lines.append(f"- Q: {t.get('question','')}")
        if t.get("sql"):
            lines.append(f"  SQL: {t['sql']}")
    return "Recent conversation:\n" + "\n".join(lines) + "\n\n"


def build_generate_messages(
    question: str, context: str, history: list[dict[str, Any]] | None, error: str | None = None
) -> list[Message]:
    user = f"{_history_block(history)}Available schema and examples:\n{context}\n\nQuestion: {question}"
    if error:
        user += f"\n\nYour previous SQL failed validation: {error}\nFix it and return corrected SQL."
    return [
        {"role": "system", "content": GENERATE_SYSTEM},
        {"role": "user", "content": user},
    ]


def parse_sql(text: str) -> str:
    """Extract SQL from a ```sql fence; fall back to the whole text."""
    m = re.search(r"```sql\s*(.+?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip(";").strip()
    m = re.search(r"```\s*(.+?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip().rstrip(";").strip()
    return text.strip().rstrip(";").strip()


def build_summarize_messages(
    question: str, sql: str, rows: list[dict[str, Any]], history: list[dict[str, Any]] | None
) -> list[Message]:
    sample = rows[:50]
    user = (
        f"{_history_block(history)}Question: {question}\n\nSQL:\n{sql}\n\n"
        f"Result rows ({len(rows)} total, first {len(sample)} shown):\n"
        f"{json.dumps(sample, default=str)}"
    )
    return [
        {"role": "system", "content": SUMMARIZE_SYSTEM},
        {"role": "user", "content": user},
    ]


def parse_summary(text: str) -> dict[str, Any]:
    """Parse the strict-JSON summary; tolerate stray fences/prose."""
    cleaned = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(1).strip()
    try:
        data = json.loads(cleaned)
    except Exception:  # noqa: BLE001
        return {"summary": text.strip(), "chart": {"type": "none"}}
    chart = data.get("chart") or {"type": "none"}
    return {"summary": data.get("summary", ""), "chart": chart}
