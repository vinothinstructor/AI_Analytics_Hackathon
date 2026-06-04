"""LIVE mode — real-time Azure OpenAI calls (office laptop, precapture, Round 3).

CRITICAL (the bug that bit Solutions 1 and 2): this client MUST fail loudly when
Azure credentials are missing. It NEVER silently falls back to mock/fake. The
check lives in __init__, so simply constructing a LiveLLMClient without creds
raises immediately and the caller surfaces a readable error.
"""
from __future__ import annotations

from ..config import settings
from .base import LLMClient, LLMMode, Message


class AzureCredentialsMissingError(RuntimeError):
    """Raised when LIVE mode is selected but Azure is not configured."""


class LiveLLMClient(LLMClient):
    mode = LLMMode.LIVE

    def __init__(self) -> None:
        missing = [
            name
            for name, value in (
                ("AZURE_OPENAI_ENDPOINT", settings.AZURE_OPENAI_ENDPOINT),
                ("AZURE_OPENAI_API_KEY", settings.AZURE_OPENAI_API_KEY),
            )
            if not value
        ]
        if missing:
            raise AzureCredentialsMissingError(
                "Azure credentials missing ("
                + ", ".join(missing)
                + ") — LIVE mode unavailable on this machine; use FAKE. "
                "LIVE requires Azure OpenAI (office laptop only)."
            )

        # Imported lazily so the package loads even where openai isn't needed.
        from openai import AzureOpenAI

        self._client = AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
        self._chat_deployment = settings.AZURE_OPENAI_CHAT_DEPLOYMENT
        self._embed_deployment = settings.AZURE_OPENAI_EMBED_DEPLOYMENT

    def chat(self, messages: list[Message], **kwargs) -> str:
        resp = self._client.chat.completions.create(
            model=self._chat_deployment,
            messages=messages,  # type: ignore[arg-type]
            temperature=kwargs.get("temperature", 0.0),
        )
        return resp.choices[0].message.content or ""

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(
            model=self._embed_deployment,
            input=texts,
        )
        return [item.embedding for item in resp.data]
