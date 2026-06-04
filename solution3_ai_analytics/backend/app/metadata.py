"""Loads the YAML data dictionary once and exposes it to the pipeline.

- SCHEMA_CACHE: {table_name -> set(column_names)} for column-existence checks.
- ALLOWED_TABLES: the 8 app.* tables the validator whitelists.
- TABLE_DESCRIPTIONS / EXAMPLES: for building generation context.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent / "config_files"


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _tables() -> list[dict]:
    return _load("tables.yaml")["tables"]


@lru_cache(maxsize=1)
def schema_cache() -> dict[str, set[str]]:
    return {t["name"]: {c["name"] for c in t["columns"]} for t in _tables()}


@lru_cache(maxsize=1)
def allowed_tables() -> set[str]:
    return set(schema_cache().keys())


@lru_cache(maxsize=1)
def table_descriptions() -> dict[str, str]:
    return {t["name"]: t["description"].strip() for t in _tables()}


@lru_cache(maxsize=1)
def table_schema_text() -> dict[str, str]:
    """Per-table 'name(col type, ...)' string for the generation prompt."""
    out = {}
    for t in _tables():
        cols = ", ".join(f"{c['name']} {c['type']}" for c in t["columns"])
        out[t["name"]] = f"app.{t['name']}({cols})"
    return out


@lru_cache(maxsize=1)
def examples() -> list[dict]:
    return _load("examples.yaml")["examples"]


@lru_cache(maxsize=1)
def demo_questions() -> dict:
    return _load("demo_questions.yaml")


@lru_cache(maxsize=1)
def _scripted_followups_map() -> dict[str, list[str]]:
    """question -> curated follow-up chips, for the scripted wow set (so the chips
    stay exact in every mode and re-ask the exact captured questions)."""
    return {
        e["question"]: list(e.get("followups", []))
        for e in demo_questions().get("scripted", [])
        if e.get("question")
    }


def scripted_followups(question: str) -> list[str] | None:
    return _scripted_followups_map().get(question.strip())
