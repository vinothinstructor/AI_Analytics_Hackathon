"""Async SQLAlchemy engines: privileged + read-only.

- `engine` / `SessionLocal` use the privileged role (seeding, meta, audit writes).
- `readonly_engine` / `ReadOnlySessionLocal` use the SELECT-only role; Phase 2
  executes generated SQL through this so a malformed/hostile query cannot write.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ..config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

readonly_engine = create_async_engine(
    settings.APP_READONLY_DATABASE_URL, echo=False, pool_pre_ping=True
)
ReadOnlySessionLocal = async_sessionmaker(readonly_engine, expire_on_commit=False)
