# Solution 3 — IQVIA AI Analytics

A configurable, embeddable natural-language-to-SQL chat widget for clinical trial
sponsors. **Phase 1** ships the running skeleton: seeded database, the embeddable
widget shell inside a mock "One Home for Sites" wrapper, the 4-mode LLM routing
wired end to end — but **no real NL2SQL pipeline yet** (that's Phase 2).

## The 4 LLM modes

Every LLM call routes through an abstraction selected per-request by the
`X-LLM-Mode` header:

| Mode   | What it does                                              | Needs Azure |
|--------|-----------------------------------------------------------|:-----------:|
| MOCK   | Template/skeleton responses. Dev plumbing only.           | no          |
| FAKE   | Hand-authored deterministic responses + heuristic fallback. **Local-dev default.** | no |
| CACHED | Replays captured *real* LIVE responses from `app/cache/*.json`. Demo-recording mode. | no |
| LIVE   | Real-time Azure OpenAI (`gpt-4.1-mini`, `text-embedding-3-small`). | **yes**     |

`LiveLLMClient` **fails loud** when Azure creds are missing — it never silently
falls back. On the personal MacBook everything runs in FAKE/LOCAL.

## Prerequisites

Docker, `uv`, `pnpm`, Node 18+. No Azure needed locally.

## Run it (personal MacBook — FAKE mode)

```bash
# 1. Database (Postgres + pgvector). Host port 55432 to avoid clashing with 5432.
docker compose up -d

# 2. Backend deps + seed + embeddings
cd backend
uv sync --python 3.11
cp .env.example .env                              # defaults are correct for local
uv run python scripts/generate_synthetic_db.py    # seeds the locked-arc data (~7s)
uv run python scripts/embed_metadata.py           # LOCAL pseudo-vectors (no Azure)

# 3. Backend (port 8003)
uv run uvicorn app.main:app --port 8003 --reload

# 4. Frontend (separate terminal) — Vite picks a free port (5173/5174/5175…)
cd frontend
pnpm install
pnpm dev
```

Open the printed Vite URL. Append `?recording=true` to hide the mode dropdown.

## Database topology

- DB `solution3`, two schemas: `app` (clinical data) + `meta` (metadata/embeddings).
- `vector` extension enabled.
- Roles: `solution3_app` (privileged — seeding, meta, audit writes) and
  `app_readonly` (SELECT-only on `app`; Phase 2 executes generated SQL through it).
- Created by `db/init/01_init.sql` (runs once, on a fresh volume).

## Phase 2 — the NL→SQL pipeline (done)

- `POST /chat` (SSE) runs the LangGraph pipeline (retrieve → generate → validate →
  execute → summarize) and streams events: `stage`, `sql`, `token`, `chart`,
  `followups`, `trust`, `error`, `done`. `GET /audit/{query_id}` returns the audit row.
- Real **sqlglot AST validation** + **tenant-filter injection** (`sponsor_id = :sponsor_id`)
  on every SELECT scope; execution is **read-only** (`app_readonly`, 5s timeout, 1000-row cap).
- Two tenants seeded: **Helix Therapeutics** (the locked arc) + **Meridian Pharmaceuticals**
  (isolation demo). FAKE mode stubs only embed/generate/summarize — validate+execute are real.
- Tests: `cd backend && uv run pytest -q` (locked arc, tenant isolation, AST validator,
  presentation fast-path) — all green in FAKE mode, no Azure.

## The locked demo arc

The hero question reproduces MOON-2026's five hero sites exactly:
Munich 82% · São Paulo 67% · Tokyo 45% · Boston 38% · Toronto 28%.
Toronto/Tokyo/Boston also show declining recent enrollment velocity and elevated
screen-failure rates. The seed is fixed (`SEED=42`) so this is reproducible.

## Office laptop (LIVE) — later

Set the `AZURE_OPENAI_*` keys in `.env`, then:
`uv run python scripts/check_azure.py` (hello-world), `embed_metadata.py --live`
(real vectors), and capture cached responses into `app/cache/` (Phase 5).

## Layout

- `backend/app/llm/` — the 4-mode abstraction + `resolve_llm_mode` dependency.
- `backend/app/pipeline/graph.py` — LangGraph scaffold (5 stub nodes).
- `backend/app/db/`, `backend/scripts/` — models + seed/embed/check scripts.
- `backend/app/config_files/` — `tables.yaml`, `columns.yaml`, `examples.yaml`.
- `frontend/src/` — One Home wrapper, widget shell, mode store + `apiFetch`.

Phases: **1 skeleton (done)** → 2 NL2SQL pipeline + SSE → 3 chat UI + charts →
4 behind-the-scenes panel → 5 question library + precapture + demo polish.
