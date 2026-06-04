-- Solution 3 database topology (runs once, on fresh volume).
-- Database `solution3` already created by POSTGRES_DB. Here we add:
--   * the pgvector extension
--   * two schemas: app (clinical data) and meta (metadata + embeddings)
--   * a privileged role (owns/seeds everything) and a SELECT-only role
--
-- Defense-in-depth: app_readonly can SELECT app data but cannot write or DDL.
-- Phase 2 executes generated SQL through the app_readonly connection.

-- pgvector lives in public so the `vector` type resolves via search_path
-- (default "$user", public) from any schema.
CREATE EXTENSION IF NOT EXISTS vector;

-- Privileged application role (seeding, meta access, audit writes).
CREATE ROLE solution3_app LOGIN PASSWORD 'app_pw';

-- Read-only role used by the Phase 2 execution path.
CREATE ROLE app_readonly LOGIN PASSWORD 'readonly_pw';

-- Schemas owned by the privileged role.
CREATE SCHEMA app AUTHORIZATION solution3_app;
CREATE SCHEMA meta AUTHORIZATION solution3_app;

-- Read-only role: USAGE on app (see objects) but no write/DDL.
GRANT USAGE ON SCHEMA app TO app_readonly;

-- Auto-grant SELECT on every table the privileged role later creates in app.
ALTER DEFAULT PRIVILEGES FOR ROLE solution3_app IN SCHEMA app
  GRANT SELECT ON TABLES TO app_readonly;

-- Explicitly DENY write paths (belt and suspenders; default is already no-grant).
-- No INSERT/UPDATE/DELETE/TRUNCATE and no schema CREATE are granted to app_readonly.
REVOKE CREATE ON SCHEMA app FROM app_readonly;
REVOKE CREATE ON SCHEMA meta FROM app_readonly;
