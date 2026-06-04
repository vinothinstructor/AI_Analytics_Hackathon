"""Azure hello-world (LIVE-only) (B10).

In LIVE mode: one tiny gpt-4.1-mini chat call + one tiny text-embedding-3-small
embed call; prints success and token/dim counts. On the personal MacBook (no
creds) it FAILS LOUD with a clear "use FAKE" message — that's the correct,
expected result locally. This is the standing proof of the fail-loud behavior.

Run:  uv run python scripts/check_azure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm.live_client import AzureCredentialsMissingError, LiveLLMClient  # noqa: E402


def main() -> int:
    try:
        client = LiveLLMClient()  # raises if Azure creds are missing
    except AzureCredentialsMissingError as exc:
        print(f"FAIL-LOUD (expected on the personal MacBook): {exc}", file=sys.stderr)
        return 1

    reply = client.chat([{"role": "user", "content": "Reply with the single word: ok"}])
    print(f"chat ok -> {reply!r}")

    vecs = client.embed(["hello world"])
    print(f"embed ok -> 1 vector of dim {len(vecs[0])}")

    print("Azure LIVE check succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
