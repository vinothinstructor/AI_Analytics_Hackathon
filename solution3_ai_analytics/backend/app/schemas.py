"""Shared Pydantic models.

Phase 1 only needs the conversation/chart groundwork (B5). The full request /
response envelopes for /chat land in Phase 2.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ChartType = Literal["bar", "line", "pie", "donut", "scatter", "area", "none"]


class ChartSpec(BaseModel):
    """How the frontend should render a result. The renderer is Phase 3; this is
    the contract Phase 2's summarize node fills in."""

    type: ChartType = "none"
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    color_field: Optional[str] = None
    title: Optional[str] = None


class Turn(BaseModel):
    """One question/answer exchange, kept for short-window conversation memory."""

    question: str
    sql: Optional[str] = None
    chart_spec: Optional[ChartSpec] = None
    # A compact digest of the result (e.g. row count + a few key figures) so the
    # presentation fast-path can re-render without re-querying. Full rows are not
    # retained in memory.
    result_digest: Optional[str] = None


class ConversationState(BaseModel):
    """Server-side conversation, capped to the last few turns by SessionStore."""

    conversation_id: str
    turns: list[Turn] = Field(default_factory=list)
