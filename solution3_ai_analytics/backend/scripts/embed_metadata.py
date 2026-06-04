"""Populate meta.table_embeddings + meta.example_embeddings (B9).

Two paths, same output table shape so Phase 2 retrieval works identically:
  * LOCAL/FAKE (default, personal MacBook): deterministic pseudo-embeddings
    (seeded NumPy RNG per text). No Azure.
  * LIVE (office laptop): real text-embedding-3-small (1536-dim) via Azure.

Path selection: --live flag, or LLM_MODE=LIVE in the environment. Default LOCAL.

Run:  uv run python scripts/embed_metadata.py            # LOCAL pseudo-vectors
      uv run python scripts/embed_metadata.py --live      # real Azure vectors
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.db import Base  # noqa: E402
from app.db.engine import engine  # noqa: E402
from app.db.meta_models import ExampleEmbedding, TableEmbedding  # noqa: E402
from app.llm.pseudo import pseudo_embed  # noqa: E402

CONFIG_DIR = Path(__file__).resolve().parent.parent / "app" / "config_files"


def _load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def _table_text(t: dict) -> str:
    cols = "; ".join(f"{c['name']} ({c['type']}): {c['description']}" for c in t["columns"])
    return f"Table {t['name']}: {t['description'].strip()} Columns: {cols}"


def _use_live() -> bool:
    return "--live" in sys.argv or settings.LLM_MODE.upper() == "LIVE"


def _embed(texts: list[str], live: bool) -> list[list[float]]:
    if live:
        from app.llm.live_client import LiveLLMClient  # fails loud if no creds

        client = LiveLLMClient()
        out: list[list[float]] = []
        for i in range(0, len(texts), 16):  # modest batch size
            out.extend(client.embed(texts[i : i + 16]))
        return out
    return [pseudo_embed(t) for t in texts]


async def main() -> None:
    live = _use_live()
    tables = _load_yaml("tables.yaml")["tables"]
    _columns = _load_yaml("columns.yaml")  # loaded per B9 (informs Phase 2 generation)
    examples = _load_yaml("examples.yaml")["examples"]

    table_texts = [_table_text(t) for t in tables]
    example_texts = [e["question"] for e in examples]

    print(f"Embedding {len(table_texts)} tables + {len(example_texts)} examples "
          f"({'LIVE Azure' if live else 'LOCAL pseudo-vectors'})...")

    table_vecs = _embed(table_texts, live)
    example_vecs = _embed(example_texts, live)

    # Ensure meta tables exist; then replace rows (vectors are deterministic).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(TableEmbedding.__table__.delete())
        await conn.execute(ExampleEmbedding.__table__.delete())
        await conn.execute(
            TableEmbedding.__table__.insert(),
            [
                {"table_name": t["name"], "description": txt, "embedding": vec}
                for t, txt, vec in zip(tables, table_texts, table_vecs)
            ],
        )
        await conn.execute(
            ExampleEmbedding.__table__.insert(),
            [
                {"question": e["question"], "sql": e["sql"], "embedding": vec}
                for e, vec in zip(examples, example_vecs)
            ],
        )

    await engine.dispose()
    print(f"Wrote {len(table_vecs)} table_embeddings and {len(example_vecs)} "
          f"example_embeddings (dim={len(table_vecs[0])}).")


if __name__ == "__main__":
    asyncio.run(main())
