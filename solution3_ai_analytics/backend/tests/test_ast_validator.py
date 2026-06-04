"""AST validator: rejects unsafe SQL; accepts valid SELECTs and injects the
tenant predicate on the anchor of every SELECT scope."""
import pytest

from app.pipeline.validate import validate_and_inject


@pytest.mark.parametrize(
    "label,sql",
    [
        ("non-select", "DELETE FROM app.sites"),
        ("multi-statement", "SELECT 1; SELECT 2"),
        ("pg_catalog", "SELECT * FROM pg_catalog.pg_tables"),
        ("meta-schema", "SELECT * FROM meta.table_embeddings"),
        ("hallucinated-column", "SELECT AVG(age) FROM app.patients p"),
        ("set-operation", "SELECT site_id FROM app.sites UNION SELECT 1"),
    ],
)
def test_validator_rejects(label, sql):
    result = validate_and_inject(sql)
    assert result["ok"] is False, f"{label} should be rejected"
    assert result["error"]


def test_validator_accepts_and_injects():
    sql = (
        "SELECT s.name, COUNT(p.patient_id) AS enrolled "
        "FROM app.sites s JOIN app.patients p ON p.site_id = s.site_id GROUP BY s.name"
    )
    result = validate_and_inject(sql)
    assert result["ok"] is True
    assert "s.sponsor_id = :sponsor_id" in result["sql_final"]
    assert "-- auto-injected" in result["sql_display"]
    assert set(result["tables_used"]) == {"sites", "patients"}


def test_validator_injects_every_scope():
    # Subquery + outer query: BOTH scopes get a tenant predicate on their anchor.
    sql = (
        "SELECT st.code, x.enrolled FROM app.studies st "
        "JOIN (SELECT s.study_id, COUNT(p.patient_id) AS enrolled "
        "FROM app.sites s LEFT JOIN app.patients p ON p.site_id = s.site_id "
        "GROUP BY s.study_id) x ON x.study_id = st.study_id"
    )
    result = validate_and_inject(sql)
    assert result["ok"] is True
    # Outer anchor (studies st) and inner anchor (sites s) both filtered.
    assert "st.sponsor_id = :sponsor_id" in result["sql_final"]
    assert "s.sponsor_id = :sponsor_id" in result["sql_final"]
