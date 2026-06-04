"""LLM abstraction layer: one ABC, four mode implementations, a resolver."""
from .base import EMBED_DIM, LLMClient, LLMMode, Message
from .resolve import build_client, resolve_llm_mode

__all__ = [
    "EMBED_DIM",
    "LLMClient",
    "LLMMode",
    "Message",
    "build_client",
    "resolve_llm_mode",
]
