# Office Machine Setup — Solution 3 (IQVIA AI Analytics), CACHED mode (no Azure OpenAI)

This guide sets up the app on the office machine, which uses a **managed Azure Database
for PostgreSQL** (no Docker for the DB) and has **no Azure OpenAI access**. The app runs
the demo purely in **CACHED** mode (replaying real Azure OpenAI responses captured
earlier).

> ⚠️ **Why a DB dump (not the seed scripts)?**
> CACHED replay does a live **pgvector** similarity search over `meta.*` to pick the
> few-shot examples. The cache keys were computed against the **real Azure-embedded**
> example bank. If you regenerate embeddings here with `embed_metadata.py` you'd get
> **LOCAL pseudo-vectors**, retrieval would return different examples, the cache keys
> would change, and CACHED would **miss**.
> **You must restore the database dump** carried from the source machine. Do **NOT**
> run `generate_synthetic_db.py` or `embed_metadata.py` on this machine.

---

## 0. Prerequisites

- **PostgreSQL 16 client tools** — `psql` and `pg_restore` (the dump is PG 16 custom
  format; `pg_restore` must be **≥ 16**). e.g. macOS: `brew install postgresql@16`.
- **uv** (Python runner) — https://docs.astral.sh/uv/
- **Node 18+** and **pnpm** (`npm i -g pnpm`)
- **Access to the Azure PostgreSQL server**: the admin login/password, and a
  **firewall rule** allowing this machine's IP (Azure Portal → your Postgres server →
  *Networking* → add client IP). SSL is required (Azure enforces it).
- No Azure **OpenAI** keys needed.

## 1. Files to carry to this machine

| Item | Where it goes | Notes |
|---|---|---|
| The repo `solution3_ai_analytics/` | anywhere | code (no `docker-compose` needed here) |
| `backend/app/cache/*.json` (27 files) | `backend/app/cache/` | the captured Azure responses **— see below** |
| `solution3_full.dump` (~1 MB) | anywhere (e.g. repo root) | the database dump |

**The cache files are currently NOT committed to git** (only `.gitkeep` is tracked,
though `.gitignore` is set up to allow the `*.json`). Either:
- commit them on the source machine so they travel with the repo:
  `git add backend/app/cache/*.json && git commit -m "demo cache"`, **or**
- copy the whole `backend/app/cache/` folder over manually.

Confirm after copy: `ls backend/app/cache/*.json | wc -l` → **27**.

---

## 2. Collect your Azure Postgres connection details

You'll need these from the Azure Portal (server *Overview* / *Connect*):

| Variable | Example |
|---|---|
| Server host | `myserver.postgres.database.azure.com` |
| Port | `5432` |
| Admin user | `pgadmin` (Flexible Server: plain name, **no** `@server` suffix) |
| Admin password | `••••••` |

Pick two passwords for the application roles you'll create: `<APP_PW>` and `<RO_PW>`.

> The app deliberately uses **two roles**: a privileged `solution3_app` (seeds/meta/audit
> writes) and a SELECT-only `app_readonly` (the role generated SQL is executed through —
> a core part of the security story shown in the demo's trust badges). Keep both.

---

## 3. Prepare the Azure database (one-time)

### 3a. Allow-list the `vector` extension on the server

Azure blocks extensions until they're allow-listed. In the Portal:
**Server → Settings → Server parameters → `azure.extensions` → enable `VECTOR` → Save**
(this may restart the server). Or with the Azure CLI:

```bash
az postgres flexible-server parameter set \
  --resource-group <RESOURCE_GROUP> --server-name <SERVER_NAME> \
  --name azure.extensions --value VECTOR
```

### 3b. Create roles + database, then enable the extension

Point the client tools at the server (run from your shell). **SSL is required.**

```bash
export PGHOST=myserver.postgres.database.azure.com
export PGPORT=5432
export PGUSER=<ADMIN_USER>
export PGPASSWORD='<ADMIN_PASSWORD>'
export PGSSLMODE=require
export PGDATABASE=postgres        # connect to the default db to create roles/database
```

Create the two application roles and the database (the admin must be a **member** of the
roles so it can restore objects owned by them):

```bash
psql -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE solution3_app LOGIN PASSWORD '<APP_PW>';
CREATE ROLE app_readonly  LOGIN PASSWORD '<RO_PW>';
GRANT solution3_app TO CURRENT_USER;
GRANT app_readonly  TO CURRENT_USER;
CREATE DATABASE solution3;
SQL
```

Enable pgvector **inside** the `solution3` database:

```bash
psql -d solution3 -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector SCHEMA public;"
```

### 3c. Restore the dump

The schemas (`app`, `meta`), all tables, the embeddings, **and** the `app_readonly`
grants are all inside the dump — so a freshly-created empty `solution3` needs nothing
else. Keep ownership (so `solution3_app` owns `app`/`meta` as the app expects); skip the
extension comment that requires superuser on Azure:

```bash
pg_restore -d solution3 --exit-on-error --no-comments solution3_full.dump
```

> `--no-comments` avoids a `COMMENT ON EXTENSION vector` step that fails on managed Azure
> (the extension is owned by a system role). Everything else restores cleanly.
> If you re-run the restore, first reset with:
> `psql -d solution3 -c "DROP SCHEMA IF EXISTS app CASCADE; DROP SCHEMA IF EXISTS meta CASCADE;"`

### 3d. Verify the restore matches the source machine

```bash
# Row counts: patients=5600, MOON-2026 sites=14, example_embeddings=41, table_embeddings=8
psql -d solution3 -tc "
select 'patients' k, count(*) v from app.patients
union all select 'moon_sites', count(*) from app.sites s
   join app.studies st on st.study_id=s.study_id where st.code='MOON-2026'
union all select 'example_embeddings', count(*) from meta.example_embeddings
union all select 'table_embeddings', count(*) from meta.table_embeddings order by k;"

# Embedding dimensions: expect 1536
psql -d solution3 -tc "select vector_dims(embedding) from meta.example_embeddings limit 1;"

# Hero query: expect Munich 82, São Paulo 67, Tokyo 45, Boston 38, Toronto 28
psql -d solution3 -tc "
select s.name, round(100.0*count(p.patient_id)/s.target_enrollment) pct
from app.sites s join app.studies st on st.study_id=s.study_id
left join app.patients p on p.site_id=s.site_id
where st.code='MOON-2026' and s.sponsor_id='helix_therapeutics'
group by s.name, s.target_enrollment order by pct desc;"

# Read-only role can SELECT (the app's runtime query path uses this role)
PGUSER=app_readonly PGPASSWORD='<RO_PW>' psql -d solution3 -tc "select count(*) from app.patients;"
```

> The "5,000 enrolled patients" shown on the dashboard is a rounded UI metric; the
> `app.patients` table legitimately holds **5600** rows (4935 randomized). 5600 is the
> correct value to expect here.

---

## 4. Backend environment file (`.env`)

`.env` is gitignored, so create it from the example. **Set CACHED, leave Azure OpenAI
blank, and point the two DB URLs at your Azure server with `?ssl=require`.**

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env`:

```ini
LLM_MODE=CACHED
DEMO_SPONSOR=helix_therapeutics

# Azure OpenAI stays BLANK (CACHED needs no Azure OpenAI):
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=

# Azure Database for PostgreSQL — note the ?ssl=require (asyncpg) on BOTH URLs:
DATABASE_URL=postgresql+asyncpg://solution3_app:<APP_PW>@myserver.postgres.database.azure.com:5432/solution3?ssl=require
APP_READONLY_DATABASE_URL=postgresql+asyncpg://app_readonly:<RO_PW>@myserver.postgres.database.azure.com:5432/solution3?ssl=require
```

> - `?ssl=require` is what the SQLAlchemy **asyncpg** driver uses (not libpq's
>   `sslmode`). If you hit an SSL error, try `?ssl=true`.
> - If a password contains special characters (`@ : / ? # %`), **URL-encode** it in the
>   connection string (e.g. `@` → `%40`).

---

## 5. Backend (port 8003)

```bash
cd backend
uv sync                              # install Python deps
uv run uvicorn app.main:app --port 8003
# health check (new terminal): "llm_mode" should echo what you set (CACHED)
curl -s localhost:8003/health
```

Quick CACHED smoke test (should stream a `chart` event, not a cache-miss error):

```bash
curl -sN -H "X-LLM-Mode: CACHED" -H "Content-Type: application/json" \
  -d '{"conversation_id":"smoke","question":"Which of my MOON-2026 sites are at risk of missing enrollment targets, and what'\''s the 60-day trend?"}' \
  localhost:8003/chat | grep -m1 "event: chart" && echo "CACHED OK"
```

## 6. Frontend (separate terminal)

```bash
cd frontend
pnpm install
pnpm dev                             # Vite prints a URL, e.g. http://localhost:5173
```

Open the printed URL. The widget reads the server's mode from `/health`, so it runs in
**CACHED**. Open the chat widget (bottom-right) and run the demo questions.

---

## 7. The demo arc (ask in this order — keys are history-dependent)

Click the hero starter chip, then its follow-up chips **in order** — the cached keys for
the follow-ups were captured with the preceding turns in conversation history:

1. **Which of my MOON-2026 sites are at risk of missing enrollment targets, and what's the 60-day trend?** → status-colored **bar**, 14 sites (Toronto/Boston/Tokyo red).
2. **Show the 60-day enrollment trend for the at-risk sites.** → **line**, chronological weeks.
3. **What's driving the screen-failure rate at Tokyo?** → Passed/Failed breakdown (~29% fail).

Standalone (starter chip, fresh conversation):
- **How do site size and screen-failure rate relate for MOON-2026?** → **scatter**.

Other captured wows (deviations, severity, cumulative, visit mix, screen-failure ranking)
also replay. A question that wasn't captured returns a clean
`CACHED mode: no captured … response` message (expected).

---

## 8. Troubleshooting

- **CACHED misses everything / wrong charts** → the DB wasn't restored from the dump
  (or `embed_metadata.py` was run here). Re-do §3: drop the `app`/`meta` schemas and
  restore again. Never regenerate embeddings on this machine.
- **`CREATE EXTENSION vector` → "extension is not allow-listed"** → finish §3a
  (`azure.extensions` = `VECTOR`) and wait for the server to apply it.
- **`pg_restore: must be member of role "solution3_app"`** → run the
  `GRANT solution3_app TO CURRENT_USER;` / `GRANT app_readonly TO CURRENT_USER;` from §3b
  as the admin before restoring.
- **`pg_restore: error: could not execute query: ERROR: must be owner of extension vector`**
  → add `--no-comments` to the `pg_restore` command (§3c).
- **Backend SSL error connecting to DB** → ensure `?ssl=require` is on **both** URLs in
  `.env`; if it persists try `?ssl=true`. Also confirm this machine's IP is in the Azure
  firewall (§0).
- **`pg_restore: unsupported version` / TOC errors** → your `pg_restore` is older than
  16; install PostgreSQL 16 client tools.
- **Frontend shows FAKE in the header** → backend `.env` `LLM_MODE` isn't `CACHED`, or
  the backend wasn't restarted after editing `.env`.
- **Cache file count isn't 27** → re-copy `backend/app/cache/` (see §1).

## 9. Optional: run the test suite

```bash
cd backend && uv run pytest -q       # 21 tests
```
