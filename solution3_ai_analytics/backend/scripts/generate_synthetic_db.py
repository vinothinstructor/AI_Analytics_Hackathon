"""Seeded synthetic clinical-operations data (B7).

Fixed random seed -> reproducible. Drops + recreates all tables, then seeds:
  5 studies · 80 sites (14 for MOON-2026) · 80 investigators · 5,000 patients ·
  50,000 visits · 200 deviations · 10,000 user_sessions · 50 study_users.

The locked demo arc is engineered exactly. The canonical "enrolled" metric is
COUNT(patients.patient_id) per site (ALL patient rows joined to the site — see
examples.yaml hero query). So for MOON-2026's five hero sites we hard-set
target_enrollment = 100 and the TOTAL number of patient rows generated, making
enrollment-vs-target come out EXACTLY:
    #3 Munich DE 82 · #7 São Paulo BR 67 · #11 Tokyo JP 45 ·
    #14 Boston US 38 · #6 Toronto CA 28
Screen failures are a SUBSET of each site's total rows (not added on top), so the
total count still equals the percentage. Toronto / Tokyo / Boston also get
front-loaded consent dates (declining recent velocity) and elevated
screen-failure rates, and are the three lowest-ranked AT RISK sites.

Run:  uv run python scripts/generate_synthetic_db.py
"""
from __future__ import annotations

import asyncio
import datetime as dt
import random
import sys
from pathlib import Path

# Make `app` importable when run as a bare script from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Base  # noqa: E402
from app.db.app_models import (  # noqa: E402
    Deviation,
    Investigator,
    Patient,
    Site,
    Study,
    StudyUser,
    UserSession,
    Visit,
)
from app.db.engine import engine  # noqa: E402

# Primary tenant. Renamed Acme -> Helix in Phase 2; the value is the only change,
# so Helix's seeded numbers stay byte-identical to the verified Phase 1 arc
# (the rng draw sequence below is untouched). A second tenant (Meridian) is
# seeded additively at the end of build_rows().
SPONSOR = "helix_therapeutics"
MERIDIAN = "meridian_pharmaceuticals"
SEED = 42
NOW = dt.date.today()

rng = random.Random(SEED)

# ---------------------------------------------------------------------------
# Studies
# ---------------------------------------------------------------------------
STUDIES = [
    # code, name, phase, therapeutic_area, status, start_offset_days, n_sites
    ("MOON-2026", "Lunar Oncology Outcomes", "Phase III", "Oncology", "Active", 400, 14),
    ("SUNRISE-2027", "Solar Cardiometabolic", "Phase II", "Cardiology", "Active", 250, 18),
    ("ORION-2026", "Orion Neuroscience", "Phase II", "Neurology", "Active", 320, 16),
    ("PEGASUS-2025", "Pegasus Immunology", "Phase III", "Immunology", "Active", 600, 16),
    ("ATLAS-2026", "Atlas Respiratory", "Phase I", "Respiratory", "Active", 180, 16),
]

# Hero MOON-2026 sites keyed by their site_id (= the "Site #" shown in the demo).
# (name, country, target_enrollment, total_patients, screen_fails, is_laggard)
# total_patients == enrolled == COUNT(patient_id); with target 100, total == pct.
# screen_fails is a SUBSET of total_patients (elevated for the three laggards).
MOON_HERO = {
    3: ("Munich", "DE", 100, 82, 4, False),     # 82% ON TRACK,  fail 4/82 ≈ 5%
    7: ("São Paulo", "BR", 100, 67, 4, False),  # 67% WATCH,     fail 4/67 ≈ 6%
    11: ("Tokyo", "JP", 100, 45, 13, True),     # 45% AT RISK,   fail 13/45 ≈ 29%
    14: ("Boston", "US", 100, 38, 11, True),    # 38% AT RISK,   fail 11/38 ≈ 29%
    6: ("Toronto", "CA", 100, 28, 9, True),     # 28% AT RISK,   fail 9/28 ≈ 32%
}
# Mid-range MOON sites fill the remaining site_ids 1..14.
MOON_MID_CITIES = [
    ("London", "GB"), ("Paris", "FR"), ("Madrid", "ES"), ("Rome", "IT"),
    ("Sydney", "AU"), ("Mumbai", "IN"), ("Seoul", "KR"), ("Mexico City", "MX"),
    ("Chicago", "US"),
]
COUNTRIES = ["US", "DE", "BR", "JP", "CA", "GB", "FR", "IT", "ES", "AU", "IN", "KR", "MX", "CN"]
SPECIALIZATIONS = ["Oncology", "Cardiology", "Neurology", "Immunology", "Respiratory", "Internal Medicine"]
USER_ROLES = ["CRA", "Data Manager", "Medical Monitor", "Study Lead", "Biostatistician"]
DEVIATION_TYPES = ["Informed Consent", "Visit Window", "Dosing Error", "Sample Handling", "Eligibility", "Reporting"]
SEVERITIES = ["minor", "major", "critical"]
VISIT_STATUSES = ["completed", "scheduled", "missed"]


def _consent_days_ago(is_laggard: bool) -> int:
    """Front-load laggard consents (old) so recent-60-day velocity tails off."""
    if is_laggard:
        return rng.randint(160, 365) if rng.random() < 0.90 else rng.randint(0, 60)
    return rng.randint(0, 240)


def build_rows():
    studies_rows, sites_rows, inv_rows, patient_rows = [], [], [], []
    visit_rows, dev_rows, user_rows, session_rows = [], [], [], []

    # --- studies ---
    study_id_by_code = {}
    for i, (code, name, phase, ta, status, off, _n) in enumerate(STUDIES, start=1):
        study_id_by_code[code] = i
        studies_rows.append(dict(
            study_id=i, sponsor_id=SPONSOR, code=code, name=name, phase=phase,
            therapeutic_area=ta, status=status, start_date=NOW - dt.timedelta(days=off),
        ))

    # --- sites ---
    # MOON-2026 sites occupy site_id 1..14 so site_id == the demo "Site #".
    moon_id = study_id_by_code["MOON-2026"]
    # per-site plan: site_id -> (total_patients, screen_fails, is_laggard)
    # total_patients == enrolled == COUNT(patient_id); screen_fails ⊆ total.
    site_plan: dict[int, tuple[int, int, bool]] = {}
    mid_iter = iter(MOON_MID_CITIES)
    for sid in range(1, 15):
        if sid in MOON_HERO:
            name, country, target, total, fails, laggard = MOON_HERO[sid]
        else:
            # Other 9 MOON sites: 55–75% (target 100), all safely ABOVE the three
            # laggards (45/38/28) so Tokyo/Boston/Toronto stay the lowest-ranked.
            name, country = next(mid_iter)
            target = 100
            total = rng.randint(55, 75)
            fails = rng.randint(3, 8)
            laggard = False
        sites_rows.append(dict(
            site_id=sid, sponsor_id=SPONSOR, study_id=moon_id,
            name=name, country=country, target_enrollment=target,
        ))
        site_plan[sid] = (total, fails, laggard)

    # Non-MOON sites: site_id 15..80 across the other four studies.
    next_sid = 15
    nonmoon_site_ids = []
    for code, _n, _p, _ta, _s, _o, n_sites in [(s[0], *s[1:]) for s in STUDIES]:
        if code == "MOON-2026":
            continue
        sid_study = study_id_by_code[code]
        for k in range(1, n_sites + 1):
            sid = next_sid
            next_sid += 1
            sites_rows.append(dict(
                site_id=sid, sponsor_id=SPONSOR, study_id=sid_study,
                name=f"{code} Site {k:02d}", country=rng.choice(COUNTRIES),
                target_enrollment=rng.randint(60, 120),
            ))
            nonmoon_site_ids.append((sid, sid_study))

    assert next_sid - 1 == 80, f"expected 80 sites, got {next_sid - 1}"

    # Distribute the remaining patients (to hit exactly 5000) across non-MOON sites.
    # site_plan values are (total_patients, screen_fails, is_laggard).
    moon_rows_total = sum(total for (total, _f, _l) in site_plan.values())
    remaining = 5000 - moon_rows_total
    assert remaining > 0, "MOON sites already exceed 5000 patients"
    weights = [rng.uniform(0.6, 1.6) for _ in nonmoon_site_ids]
    wsum = sum(weights)
    counts = [int(remaining * w / wsum) for w in weights]
    counts[-1] += remaining - sum(counts)  # balancer -> exact 5000
    for (sid, _study), total in zip(nonmoon_site_ids, counts):
        fails = round(total * rng.uniform(0.05, 0.20))  # screen fails ⊆ total
        site_plan[sid] = (total, fails, False)

    # --- investigators (one per site) ---
    study_id_by_site = {r["site_id"]: r["study_id"] for r in sites_rows}
    for sid in range(1, 81):
        inv_rows.append(dict(
            inv_id=sid, sponsor_id=SPONSOR, site_id=sid,
            name=f"Dr. Investigator {sid:02d}", specialization=rng.choice(SPECIALIZATIONS),
        ))

    # --- patients ---
    # Each site generates EXACTLY `total` rows (= COUNT(patient_id) = enrolled).
    # `fails` of them are screen failures (a subset); the rest passed/randomized.
    # All consent dates use _consent_days_ago(laggard) so laggard sites tail off
    # over the last 60 days regardless of pass/fail.
    patient_id = 0
    for sid in range(1, 81):
        total, fails, laggard = site_plan[sid]
        passes = total - fails
        study_id = study_id_by_site[sid]
        for _ in range(passes):  # passed screening -> randomized
            patient_id += 1
            patient_rows.append(dict(
                patient_id=patient_id, sponsor_id=SPONSOR, site_id=sid, study_id=study_id,
                consent_date=NOW - dt.timedelta(days=_consent_days_ago(laggard)),
                screen_pass=True, randomized=True,
            ))
        for _ in range(fails):  # screen failures (still counted in enrolled total)
            patient_id += 1
            patient_rows.append(dict(
                patient_id=patient_id, sponsor_id=SPONSOR, site_id=sid, study_id=study_id,
                consent_date=NOW - dt.timedelta(days=_consent_days_ago(laggard)),
                screen_pass=False, randomized=False,
            ))
    assert patient_id == 5000, f"expected 5000 patients, got {patient_id}"
    total_patients = patient_id

    # --- visits (50,000) ---
    site_of_patient = {r["patient_id"]: r["site_id"] for r in patient_rows}
    for vid in range(1, 50_001):
        pid = rng.randint(1, total_patients)
        planned = NOW - dt.timedelta(days=rng.randint(0, 200))
        status = rng.choices(VISIT_STATUSES, weights=[70, 20, 10])[0]
        actual = planned + dt.timedelta(days=rng.randint(0, 5)) if status == "completed" else None
        visit_rows.append(dict(
            visit_id=vid, sponsor_id=SPONSOR, patient_id=pid,
            planned_date=planned, actual_date=actual, status=status,
        ))

    # --- deviations (200, clustered at the underperforming sites) ---
    laggard_sites = [6, 11, 14]
    for did in range(1, 201):
        if rng.random() < 0.5:
            sid = rng.choice(laggard_sites)
        else:
            sid = rng.randint(1, 80)
        dev_rows.append(dict(
            deviation_id=did, sponsor_id=SPONSOR, study_id=study_id_by_site[sid], site_id=sid,
            type=rng.choice(DEVIATION_TYPES),
            severity=rng.choices(SEVERITIES, weights=[60, 30, 10])[0],
            occurred_date=NOW - dt.timedelta(days=rng.randint(0, 180)),
        ))

    # --- study_users (50) ---
    for uid in range(1, 51):
        user_rows.append(dict(
            user_id=uid, sponsor_id=SPONSOR, name=f"User {uid:02d}",
            email=f"user{uid:02d}@helix-therapeutics.example", role=rng.choice(USER_ROLES),
        ))

    # --- user_sessions (10,000): 2 power users, 3 abandoned, rest moderate ---
    user_weight = {}
    for uid in range(1, 51):
        if uid in (1, 2):
            user_weight[uid] = 8.0          # power users
        elif uid in (3, 4, 5):
            user_weight[uid] = 0.05         # abandoned
        else:
            user_weight[uid] = 1.0          # moderate (2-3x/week shape)
    wsum = sum(user_weight.values())
    per_user = {uid: int(10_000 * w / wsum) for uid, w in user_weight.items()}
    per_user[50] += 10_000 - sum(per_user.values())  # balancer -> exact 10,000
    session_id = 0
    for uid in range(1, 51):
        for _ in range(per_user[uid]):
            session_id += 1
            session_rows.append(dict(
                session_id=session_id, sponsor_id=SPONSOR, user_id=uid,
                login_date=NOW - dt.timedelta(days=rng.randint(0, 180)),
                duration_seconds=rng.randint(60, 3600),
            ))
    assert session_id == 10_000, f"expected 10000 sessions, got {session_id}"

    # -----------------------------------------------------------------------
    # Second tenant — Meridian Pharmaceuticals (additive; ID ranges offset so
    # Helix is untouched). Smaller, clearly distinct: 3 studies, 24 sites, 600
    # patients, 3,000 visits, 30 deviations, 12 users, 800 sessions. Different
    # study codes (no MOON-2026). Exists so tenant isolation is demonstrable.
    # -----------------------------------------------------------------------
    MERIDIAN_STUDIES = [
        ("HALO-2027", "Halo Dermatology", "Phase II", "Dermatology", "Active", 200),
        ("VERTEX-2026", "Vertex Endocrinology", "Phase III", "Endocrinology", "Active", 480),
        ("COMET-2025", "Comet Hematology", "Phase I", "Hematology", "Active", 300),
    ]
    m_study_id = {}
    for offset, (code, name, phase, ta, status, off) in enumerate(MERIDIAN_STUDIES):
        sid_study = 6 + offset  # Helix used 1..5
        m_study_id[code] = sid_study
        studies_rows.append(dict(
            study_id=sid_study, sponsor_id=MERIDIAN, code=code, name=name, phase=phase,
            therapeutic_area=ta, status=status, start_date=NOW - dt.timedelta(days=off),
        ))

    # 24 sites: 8 per study, site_id 81..104 (Helix used 1..80).
    m_site_study = {}
    m_site_ids = []
    next_site = 81
    for code, *_ in MERIDIAN_STUDIES:
        for k in range(1, 9):
            sid = next_site
            next_site += 1
            sites_rows.append(dict(
                site_id=sid, sponsor_id=MERIDIAN, study_id=m_study_id[code],
                name=f"{code} Site {k:02d}", country=rng.choice(COUNTRIES),
                target_enrollment=rng.randint(60, 120),
            ))
            m_site_study[sid] = m_study_id[code]
            m_site_ids.append(sid)
        # one investigator per site
    for sid in m_site_ids:
        inv_rows.append(dict(
            inv_id=sid, sponsor_id=MERIDIAN, site_id=sid,
            name=f"Dr. Meridian {sid:02d}", specialization=rng.choice(SPECIALIZATIONS),
        ))

    # 600 patients across the 24 sites.
    m_weights = [rng.uniform(0.6, 1.6) for _ in m_site_ids]
    m_wsum = sum(m_weights)
    m_counts = [int(600 * w / m_wsum) for w in m_weights]
    m_counts[-1] += 600 - sum(m_counts)
    m_patient_id = 5000  # Helix used 1..5000
    for sid, total in zip(m_site_ids, m_counts):
        fails = round(total * rng.uniform(0.05, 0.20))
        passes = total - fails
        study_id = m_site_study[sid]
        for _ in range(passes):
            m_patient_id += 1
            patient_rows.append(dict(
                patient_id=m_patient_id, sponsor_id=MERIDIAN, site_id=sid, study_id=study_id,
                consent_date=NOW - dt.timedelta(days=_consent_days_ago(False)),
                screen_pass=True, randomized=True,
            ))
        for _ in range(fails):
            m_patient_id += 1
            patient_rows.append(dict(
                patient_id=m_patient_id, sponsor_id=MERIDIAN, site_id=sid, study_id=study_id,
                consent_date=NOW - dt.timedelta(days=_consent_days_ago(False)),
                screen_pass=False, randomized=False,
            ))
    assert m_patient_id == 5600, f"expected 600 Meridian patients, got {m_patient_id - 5000}"

    # 3,000 visits (visit_id 50001..53000).
    for vid in range(50_001, 53_001):
        pid = rng.randint(5001, 5600)
        planned = NOW - dt.timedelta(days=rng.randint(0, 200))
        status = rng.choices(VISIT_STATUSES, weights=[70, 20, 10])[0]
        actual = planned + dt.timedelta(days=rng.randint(0, 5)) if status == "completed" else None
        visit_rows.append(dict(
            visit_id=vid, sponsor_id=MERIDIAN, patient_id=pid,
            planned_date=planned, actual_date=actual, status=status,
        ))

    # 30 deviations (deviation_id 201..230).
    for did in range(201, 231):
        sid = rng.choice(m_site_ids)
        dev_rows.append(dict(
            deviation_id=did, sponsor_id=MERIDIAN, study_id=m_site_study[sid], site_id=sid,
            type=rng.choice(DEVIATION_TYPES),
            severity=rng.choices(SEVERITIES, weights=[60, 30, 10])[0],
            occurred_date=NOW - dt.timedelta(days=rng.randint(0, 180)),
        ))

    # 12 users (user_id 51..62) + 800 sessions (session_id 10001..10800).
    for uid in range(51, 63):
        user_rows.append(dict(
            user_id=uid, sponsor_id=MERIDIAN, name=f"Meridian User {uid:02d}",
            email=f"user{uid:02d}@meridian-pharma.example", role=rng.choice(USER_ROLES),
        ))
    for sess in range(10_001, 10_801):
        session_rows.append(dict(
            session_id=sess, sponsor_id=MERIDIAN, user_id=rng.randint(51, 62),
            login_date=NOW - dt.timedelta(days=rng.randint(0, 180)),
            duration_seconds=rng.randint(60, 3600),
        ))

    return {
        Study: studies_rows, Site: sites_rows, Investigator: inv_rows,
        Patient: patient_rows, Visit: visit_rows, Deviation: dev_rows,
        StudyUser: user_rows, UserSession: session_rows,
    }


async def main() -> None:
    data = build_rows()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Insert in FK-safe order, chunked.
    order = [Study, Site, Investigator, StudyUser, Patient, Visit, Deviation, UserSession]
    async with engine.begin() as conn:
        for model in order:
            rows = data[model]
            table = model.__table__
            for i in range(0, len(rows), 5000):
                await conn.execute(table.insert(), rows[i : i + 5000])
            print(f"  seeded {len(rows):>6} rows -> {table.schema}.{table.name}")

    await engine.dispose()
    print("Synthetic database seeded successfully (seed=%d, as-of=%s)." % (SEED, NOW))


if __name__ == "__main__":
    asyncio.run(main())
