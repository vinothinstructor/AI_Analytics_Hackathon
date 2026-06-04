# Recording & LIVE-Capture Runbook (office laptop)

This is the exact checklist to capture real Azure responses and record the demo.
Do it on the **office MacBook** (which has Azure: `gpt-4.1-mini` +
`text-embedding-3-small`). The personal MacBook (FAKE mode) cannot run LIVE.

## 0. Prereqs
- Docker running; `uv`, `pnpm`, Node installed.
- Azure OpenAI access for the locked deployment (same as Solution 2).

## 1. Configure Azure (LIVE)
In `backend/.env` set:
```
LLM_MODE=LIVE
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-small
```
Then sanity-check Azure:
```
cd backend && uv run python scripts/check_azure.py     # must print success (chat + embed)
```

## 2. Database (deterministic seed)
```
docker compose up -d
cd backend
uv run python scripts/generate_synthetic_db.py        # SEED=42 → locked arc 82/67/45/38/28
```

## 3. Real metadata embeddings (LIVE) — commit them
```
uv run python scripts/embed_metadata.py --live        # real text-embedding-3-small, 1536-dim
```
Commit `meta.table_embeddings` + `meta.example_embeddings` content as captured
(or re-run on the recording machine; they must match what precache used).

## 4. Precapture the scripted arc (LIVE) — commit the cache
```
uv run python scripts/precache.py                     # LIVE (LLM_MODE=LIVE) — real Azure capture
```
This runs hero → follow-up A → follow-up B → presentation-change with a stable
`conversation_id`, writing real Azure responses to `app/cache/*.json` under the
frozen key scheme. Review the printed summary (turns, keys, files, misses=0).
Commit `backend/app/cache/*.json`.

> Dry-run equivalent on any machine (no Azure), to test the mechanism:
> `uv run python scripts/precache.py --dry-run`

## 5. Verify CACHED replay + reproducibility
```
uv run pytest -q                                       # all green incl. test_recording_reproducibility
# Manual: backend up, frontend up, open ?recording=true and run the scripted arc.
```
Confirm the hero shows 82/67/45/38/28, the follow-ups and presentation fast-path
work, and a deliberately-unmapped question raises a clean cache-miss error.

## 6. Run the app
```
# terminal 1
cd backend && uv run uvicorn app.main:app --port 8003
# terminal 2
cd frontend && pnpm install && pnpm dev
```

## 7. Record (Round 2 — CACHED)
Open the app with **`?recording=true&mode=CACHED`** — `recording=true` hides the
mode dropdown + all dev affordances, and the explicit `mode=CACHED` replays the
captured real Azure responses deterministically. (`?recording=true` alone keeps
whatever mode is selected — FAKE by default — so you MUST pass `&mode=CACHED` for
the real recording.) Optional insurance:
- `&autotype=1` — auto-types the hero on panel open (e.g. `?recording=true&mode=CACHED&autotype=1`).
- Press **F2** any time (recording only) to auto-type the hero as a safety net.
Drive the scripted arc; everything replays the captured real Azure responses.

## 8. Round 3 — LIVE defense
Run normally (LLM_MODE=LIVE, no `?recording`). Use the mode dropdown to switch
CACHED ↔ LIVE in front of judges; unrehearsed in-domain questions generate novel
SQL on the spot. The `safe_extras` in `app/config_files/demo_questions.yaml` are
good judge-prompt candidates.

## Pacing knob
Agent-reasoning stage dwell: `STAGE_DWELL_MS` in
`frontend/src/components/chat/AgentReasoning.tsx` (currently **400ms**). Tune for
the recording cadence.

## Notes
- Cache-key scheme is frozen: `sha256(canonical-json(messages))[:16]` (history
  included). Do not change it — captured keys must match on replay.
- Embeddings: no `dimensions` arg (default 1536). Models locked.
- The FAKE-dry-run cache (`--dry-run`) is for mechanism testing only; the
  committed recording cache must be the **LIVE** capture from step 4.
