"""AST validator + tenant-filter injection (B3) — the safety-critical core.

sqlglot (postgres dialect). Steps, in order:
  1. parse
  2. single statement, SELECT-only (no set operations)
  3. forbidden DDL/DML tokens
  4. table whitelist (only the 8 app.* tables)
  5. column existence (catches hallucinated columns like "age")
  6. tenant-filter injection on the anchor of every SELECT scope
  7. re-parse to confirm validity; render sql_final + sql_display

Returns {ok, sql_final, sql_display, tables_used, error}.
"""
from __future__ import annotations

from typing import Optional, TypedDict

import sqlglot
from sqlglot import exp

from ..metadata import allowed_tables, schema_cache

TENANT_PARAM = "sponsor_id"  # rendered as :sponsor_id, bound at execution

# DDL/DML node types that must never appear in a read-only query. Built with
# getattr so it survives minor sqlglot version differences.
_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Drop", "Alter", "Create", "Command",
    "Merge", "TruncateTable", "Grant", "Copy",
]
FORBIDDEN_TYPES = tuple(
    getattr(exp, name) for name in _FORBIDDEN_NAMES if hasattr(exp, name)
)
SET_OP_TYPES = tuple(
    getattr(exp, name) for name in ("Union", "Intersect", "Except") if hasattr(exp, name)
)


class ValidationResult(TypedDict):
    ok: bool
    sql_final: Optional[str]
    sql_display: Optional[str]
    tables_used: list[str]
    error: Optional[str]


def _fail(reason: str) -> ValidationResult:
    return {"ok": False, "sql_final": None, "sql_display": None, "tables_used": [], "error": reason}


def extract_tables(sql: str) -> list[str]:
    """Best-effort list of app tables a SQL string references (for the generate
    stage's detail line). Returns [] on parse failure."""
    try:
        stmt = sqlglot.parse_one(sql, dialect="postgres")
    except Exception:  # noqa: BLE001
        return []
    out: list[str] = []
    for t in stmt.find_all(exp.Table):
        if t.name not in out:
            out.append(t.name)
    return out


def _alias_map(tree: exp.Expression) -> dict[str, str]:
    """alias-or-name -> real table name, for every table reference in the tree."""
    out: dict[str, str] = {}
    for t in tree.find_all(exp.Table):
        out[t.alias_or_name] = t.name
    return out


def _output_aliases(tree: exp.Expression) -> set[str]:
    """SELECT-list output aliases (allowed as unqualified refs in ORDER/GROUP/HAVING)."""
    names: set[str] = set()
    for alias in tree.find_all(exp.Alias):
        names.add(alias.alias_or_name)
    return names


def _top_level_conjuncts(where: Optional[exp.Where]) -> list[exp.Expression]:
    """Direct AND-conjuncts of a scope's WHERE — does NOT descend into nested
    subqueries (their predicates belong to their own SELECT scope)."""
    if where is None:
        return []

    def split(e: exp.Expression) -> list[exp.Expression]:
        if isinstance(e, exp.Paren):
            return split(e.this)
        if isinstance(e, exp.And):
            return split(e.left) + split(e.right)
        return [e]

    return split(where.this)


def _scope_has_tenant_filter(where: Optional[exp.Where], alias: str, table_name: str) -> bool:
    """True if this scope's WHERE already AND-includes `<anchor>.sponsor_id = :sponsor_id`
    (qualified to the anchor alias/name, or unqualified in a single-table scope).
    Only matches our enforced placeholder form — never a literal — so we never skip
    injecting real tenant enforcement."""
    for c in _top_level_conjuncts(where):
        if not isinstance(c, exp.EQ):
            continue
        col = c.left if isinstance(c.left, exp.Column) else (
            c.right if isinstance(c.right, exp.Column) else None
        )
        ph = c.right if isinstance(c.right, exp.Placeholder) else (
            c.left if isinstance(c.left, exp.Placeholder) else None
        )
        if col is None or ph is None:
            continue
        if col.name == TENANT_PARAM and ph.this == TENANT_PARAM and col.table in ("", alias, table_name):
            return True
    return False


def validate_and_inject(sql: str) -> ValidationResult:
    cache = schema_cache()
    allowed = allowed_tables()

    # 1. parse
    try:
        statements = [s for s in sqlglot.parse(sql, dialect="postgres") if s is not None]
    except Exception as e:  # noqa: BLE001
        return _fail(f"SQL did not parse: {e}")
    if len(statements) != 1:
        return _fail("Only a single SQL statement is allowed.")
    stmt = statements[0]

    # 2. SELECT-only, no set operations
    if SET_OP_TYPES and list(stmt.find_all(*SET_OP_TYPES)):
        return _fail("Set operations (UNION/INTERSECT/EXCEPT) are not allowed.")
    if not isinstance(stmt, exp.Select):
        return _fail("Only read-only SELECT statements are allowed.")

    # 3. forbidden DDL/DML node types
    if FORBIDDEN_TYPES and list(stmt.find_all(*FORBIDDEN_TYPES)):
        return _fail("Statement contains a forbidden (write/DDL) operation.")

    # Query-local relations that are NOT base tables: WITH/CTE names and
    # derived-table (subquery) aliases. These are defined by the query itself.
    cte_names = {c.alias_or_name for c in stmt.find_all(exp.CTE)}
    subquery_aliases = {s.alias for s in stmt.find_all(exp.Subquery) if s.alias}

    # 4. table whitelist — only app.* base tables. References to a WITH-defined
    # relation (a CTE) are query-local, not base tables, so they're exempt.
    tables_used: list[str] = []
    for t in stmt.find_all(exp.Table):
        if t.name in cte_names and not t.db:
            continue  # reference to a CTE, not a base table
        if t.db and t.db.lower() not in ("app", ""):
            return _fail(f"Table schema '{t.db}' is not allowed (only app.*).")
        if t.name not in allowed:
            return _fail(f"Table '{t.name}' is not in the allowed schema.")
        if t.name not in tables_used:
            tables_used.append(t.name)

    # alias-or-name -> real relation. A CTE referenced as `moon_sites ms` is an
    # exp.Table(name=moon_sites, alias=ms), so alias_map['ms'] == 'moon_sites'.
    alias_map = _alias_map(stmt)
    # Every query-local relation reference (CTE names, their aliases, subquery
    # aliases) — columns from these can't be checked against the base schema.
    local_relations = cte_names | subquery_aliases | {
        a for a, real in alias_map.items() if real in cte_names
    }
    referenced_base = {real for real in alias_map.values() if real in cache}
    out_aliases = _output_aliases(stmt)

    # 5. column existence — base-table columns are STILL strictly checked; columns
    # from CTEs / derived tables are accepted (the engine resolves them).
    for col in stmt.find_all(exp.Column):
        name = col.name
        if name == "*" or col.find(exp.Star):
            continue
        qualifier = col.table
        if qualifier:
            if qualifier in local_relations:
                continue  # CTE / derived-table column — allowed
            real = alias_map.get(qualifier, qualifier)
            if real in cte_names:
                continue
            if real not in cache:
                return _fail(f"Unknown table/alias '{qualifier}' for column '{name}'.")
            if name not in cache[real]:
                return _fail(f"Column '{qualifier}.{name}' does not exist.")
        else:
            if name in out_aliases:
                continue
            if any(name in cache[rt] for rt in referenced_base):
                continue
            if local_relations:
                continue  # CTE/derived columns can't be enumerated — allow
            return _fail(f"Column '{name}' does not exist on any referenced table.")

    # Normalize any model-supplied bind placeholders (e.g. :sponsor, copied from
    # the few-shot examples) to the single enforced tenant param FIRST — so the
    # de-dup below recognizes a model-written `alias.sponsor_id = :sponsor` as the
    # same enforced predicate we'd inject and doesn't add a duplicate. (Placeholders
    # in this app are only ever the tenant; all literals are inlined.)
    for ph in stmt.find_all(exp.Placeholder):
        ph.set("this", TENANT_PARAM)

    # 6. tenant-filter injection on the base-table anchor of every SELECT scope
    # (incl. the SELECTs INSIDE each CTE that reads base tables — so wrapping a
    # query in a CTE can NOT bypass tenant isolation). CTE/derived-table anchors
    # are skipped: their underlying base reads are already filtered. The filter is
    # injected exactly ONCE per scope — if the model already wrote the same
    # `anchor.sponsor_id = :sponsor_id` predicate, we don't duplicate it.
    # (Access the direct FROM arg — key is "from_" in current sqlglot, "from" in
    # older versions — NOT select.find(exp.From), which could descend into a
    # subquery in the SELECT list.)
    for select in list(stmt.find_all(exp.Select)):
        from_ = select.args.get("from") or select.args.get("from_")
        if not from_:
            continue
        anchor = from_.this
        if not isinstance(anchor, exp.Table):
            continue  # derived table / subquery handled by its own SELECT scope
        if anchor.name in cte_names and not anchor.db:
            continue  # CTE reference, not a base table — skip (inner read is filtered)
        if anchor.name not in allowed:
            continue  # safety: only inject on a known base table
        alias = anchor.alias_or_name
        if _scope_has_tenant_filter(select.args.get("where"), alias, anchor.name):
            continue  # already tenant-filtered on this anchor — do not duplicate
        cond = exp.column(TENANT_PARAM, table=alias).eq(exp.Placeholder(this=TENANT_PARAM))
        select.where(cond, append=True, copy=False)

    # 7. re-parse + render. Postgres dialect renders a named placeholder as
    # %(sponsor_id)s; normalize to :sponsor_id (SQLAlchemy text() bind style and
    # the mockup display). Only our injected param is named, so this is safe.
    sql_final = stmt.sql(dialect="postgres").replace(
        f"%({TENANT_PARAM})s", f":{TENANT_PARAM}"
    )
    try:
        sqlglot.parse_one(sql_final, dialect="postgres")
    except Exception as e:  # noqa: BLE001
        return _fail(f"Injected SQL failed to re-parse: {e}")

    sql_display = (
        stmt.sql(dialect="postgres", pretty=True)
        .replace(f"%({TENANT_PARAM})s", f":{TENANT_PARAM}")
        .replace(
            f"{TENANT_PARAM} = :{TENANT_PARAM}",
            f"{TENANT_PARAM} = :{TENANT_PARAM} -- auto-injected",
        )
    )

    return {
        "ok": True,
        "sql_final": sql_final,
        "sql_display": sql_display,
        "tables_used": tables_used,
        "error": None,
    }
