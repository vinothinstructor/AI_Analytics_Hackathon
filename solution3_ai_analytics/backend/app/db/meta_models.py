"""Metadata + embedding tables in the `meta` schema (B7).

Both embedding tables are written by scripts/embed_metadata.py — with real
text-embedding-3-small vectors on the office laptop (LIVE) or deterministic
pseudo-vectors locally (LOCAL/FAKE). Same shape either way, so Phase 2
retrieval works identically.
"""
from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..llm.base import EMBED_DIM
from .base import Base

SCHEMA = "meta"


class TableEmbedding(Base):
    __tablename__ = "table_embeddings"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))


class ExampleEmbedding(Base):
    __tablename__ = "example_embeddings"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text)
    sql: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
