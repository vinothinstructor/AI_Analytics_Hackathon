"""Read-only overview stats for the One Home wrapper stat cards (B3).

A fixed, tenant-scoped read (NOT NL→SQL) through the SELECT-only app_readonly
connection. Scoped to the demo sponsor (Helix) like everything else.
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from ..config import settings
from ..db.engine import ReadOnlySessionLocal
from ..metadata import demo_questions

router = APIRouter()


@router.get("/demo-questions")
def get_demo_questions() -> dict:
    """The curated demo question set (single source of truth). The frontend's
    starter chips read `starters` from here so they stay in sync."""
    dq = demo_questions()
    return {
        "starters": dq.get("starters", []),
        "scripted": dq.get("scripted", []),
        "supporting_extras": dq.get("supporting_extras", []),
        "decline_demonstrators": dq.get("decline_demonstrators", []),
    }


@router.get("/overview-stats")
async def overview_stats() -> dict:
    sponsor = settings.DEMO_SPONSOR
    async with ReadOnlySessionLocal() as s:
        async with s.begin():
            await s.execute(text("SET LOCAL statement_timeout = 5000"))
            active_studies = (await s.execute(
                text("SELECT count(*) FROM app.studies WHERE sponsor_id = :sp AND status = 'Active'"),
                {"sp": sponsor},
            )).scalar_one()
            total_sites = (await s.execute(
                text("SELECT count(*) FROM app.sites WHERE sponsor_id = :sp"), {"sp": sponsor},
            )).scalar_one()
            enrolled_patients = (await s.execute(
                text("SELECT count(*) FROM app.patients WHERE sponsor_id = :sp"), {"sp": sponsor},
            )).scalar_one()
            at_risk_sites = (await s.execute(
                text(
                    """
                    SELECT count(*) FROM (
                      SELECT s.site_id
                      FROM app.sites s
                      JOIN app.studies st ON st.study_id = s.study_id
                      LEFT JOIN app.patients p ON p.site_id = s.site_id
                      WHERE st.code = 'MOON-2026' AND s.sponsor_id = :sp
                      GROUP BY s.site_id, s.target_enrollment
                      HAVING 100.0 * count(p.patient_id) / s.target_enrollment < 50
                    ) x
                    """
                ),
                {"sp": sponsor},
            )).scalar_one()
            studies = (await s.execute(
                text(
                    "SELECT code, name, phase, therapeutic_area FROM app.studies "
                    "WHERE sponsor_id = :sp ORDER BY start_date DESC"
                ),
                {"sp": sponsor},
            )).all()

    return {
        "active_studies": active_studies,
        "total_sites": total_sites,
        "enrolled_patients": enrolled_patients,
        "at_risk_sites": at_risk_sites,
        "studies": [
            {"code": r.code, "name": r.name, "phase": r.phase, "therapeutic_area": r.therapeutic_area}
            for r in studies
        ],
    }
