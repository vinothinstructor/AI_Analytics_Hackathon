"""retrieve-stage helpers: real pgvector cosine search over meta.* + context build.

Uses the privileged engine (meta is not granted to app_readonly). The embedding
vector comes from the active LLM client (LOCAL pseudo-vectors in FAKE, real Azure
in LIVE) — so the same retrieval code runs in every mode.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ..db.engine import SessionLocal
from ..db.meta_models import ExampleEmbedding, TableEmbedding
from ..metadata import table_schema_text


async def retrieve_context(query_vector: list[float], k_tables: int = 8, k_examples: int = 5) -> dict[str, Any]:
    async with SessionLocal() as session:
        t_rows = (
            await session.execute(
                select(TableEmbedding.table_name, TableEmbedding.description)
                .order_by(TableEmbedding.embedding.cosine_distance(query_vector))
                .limit(k_tables)
            )
        ).all()
        e_rows = (
            await session.execute(
                select(ExampleEmbedding.question, ExampleEmbedding.sql)
                .order_by(ExampleEmbedding.embedding.cosine_distance(query_vector))
                .limit(k_examples)
            )
        ).all()

    tables = [r.table_name for r in t_rows]
    examples = [{"question": r.question, "sql": r.sql} for r in e_rows]
    return {"tables": tables, "examples": examples, "context_text": build_context_text(tables, examples)}


def build_context_text(tables: list[str], examples: list[dict[str, str]]) -> str:
    schema = table_schema_text()
    lines = ["Tables:"]
    for t in tables:
        if t in schema:
            lines.append(f"  {schema[t]}")
    lines.append("\nExamples:")
    for ex in examples:
        sql_one_line = " ".join(ex["sql"].split())
        lines.append(f"  Q: {ex['question']}\n  SQL: {sql_one_line}")
    return "\n".join(lines)
