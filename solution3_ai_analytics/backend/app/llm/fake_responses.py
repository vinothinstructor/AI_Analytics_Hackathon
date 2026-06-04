"""FAKE-mode hand-authored demo responses + heuristic fallback (B6).

FAKE stubs ONLY the three LLM-dependent steps (embed, generate, summarize). The
SQL authored here still runs for real through the validator + app_readonly, so
chart data is genuine. The hero arc is reproduced verbatim from the approved
mockup; everything else falls back to best-effort heuristics.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from ..metadata import allowed_tables

KNOWN_SITES = [
    "Munich", "São Paulo", "Sao Paulo", "Tokyo", "Boston", "Toronto", "London",
    "Paris", "Madrid", "Rome", "Sydney", "Mumbai", "Seoul", "Mexico City", "Chicago",
]

# --- canonical demo SQL (no tenant filter — the validator injects it) ----------

HERO_SQL = """SELECT s.site_id, s.name, s.country, s.target_enrollment,
       COUNT(p.patient_id) AS enrolled,
       ROUND(100.0 * COUNT(p.patient_id) / s.target_enrollment) AS pct_of_target,
       CASE
         WHEN 100.0 * COUNT(p.patient_id) / s.target_enrollment >= 80 THEN 'ON TRACK'
         WHEN 100.0 * COUNT(p.patient_id) / s.target_enrollment >= 50 THEN 'WATCH'
         ELSE 'AT RISK'
       END AS status
FROM app.sites s
JOIN app.studies st ON st.study_id = s.study_id
LEFT JOIN app.patients p ON p.site_id = s.site_id
WHERE st.code = 'MOON-2026'
GROUP BY s.site_id, s.name, s.country, s.target_enrollment
ORDER BY pct_of_target ASC"""

# Follow-up A — "healthy vs stalled" multi-line (Munich climbing; at-risk flat).
TREND_SQL = """SELECT s.name,
       to_char(date_trunc('week', p.consent_date), 'YYYY-MM-DD') AS week,
       COUNT(p.patient_id) AS enrolled
FROM app.sites s
JOIN app.studies st ON st.study_id = s.study_id
JOIN app.patients p ON p.site_id = s.site_id
WHERE st.code = 'MOON-2026'
  AND s.name IN ('Munich', 'Tokyo', 'Boston', 'Toronto')
  AND p.consent_date >= CURRENT_DATE - INTERVAL '60 days'
GROUP BY s.name, date_trunc('week', p.consent_date)
ORDER BY date_trunc('week', p.consent_date)"""

SCREENFAIL_SQL = """SELECT s.name,
       p.screen_pass,
       COUNT(p.patient_id) AS patients
FROM app.sites s
JOIN app.patients p ON p.site_id = s.site_id
WHERE s.name = 'Tokyo'
GROUP BY s.name, p.screen_pass
ORDER BY p.screen_pass"""

# Wow #4 — deviations concentrated by site (ranked bar).
DEV_SITE_SQL = """SELECT s.name, COUNT(d.deviation_id) AS deviations
FROM app.sites s
JOIN app.studies st ON st.study_id = s.study_id
LEFT JOIN app.deviations d ON d.site_id = s.site_id
WHERE st.code = 'MOON-2026'
GROUP BY s.name
ORDER BY deviations DESC"""

# Wow #5 — site size vs screen-failure (scatter, status-colored).
SCATTER_SQL = """SELECT s.name,
       COUNT(p.patient_id) AS enrolled,
       ROUND(100.0 * COUNT(*) FILTER (WHERE NOT p.screen_pass) / COUNT(*), 1) AS screen_fail_pct,
       CASE
         WHEN 100.0 * COUNT(p.patient_id) / s.target_enrollment >= 80 THEN 'ON TRACK'
         WHEN 100.0 * COUNT(p.patient_id) / s.target_enrollment >= 50 THEN 'WATCH'
         ELSE 'AT RISK'
       END AS status
FROM app.sites s
JOIN app.studies st ON st.study_id = s.study_id
JOIN app.patients p ON p.site_id = s.site_id
WHERE st.code = 'MOON-2026'
GROUP BY s.site_id, s.name, s.target_enrollment
ORDER BY enrolled"""

# Wow #6 — cumulative enrollment over the past year (area).
CUMULATIVE_SQL = """SELECT to_char(date_trunc('month', p.consent_date), 'YYYY-MM') AS month,
       COUNT(*) AS monthly,
       SUM(COUNT(*)) OVER (ORDER BY date_trunc('month', p.consent_date)) AS cumulative
FROM app.patients p
JOIN app.studies st ON st.study_id = p.study_id
WHERE st.code = 'MOON-2026'
GROUP BY date_trunc('month', p.consent_date)
ORDER BY date_trunc('month', p.consent_date)"""

# Wow #7 — deviations by severity (donut).
SEVERITY_SQL = """SELECT d.severity, COUNT(*) AS n
FROM app.deviations d
GROUP BY d.severity
ORDER BY n DESC"""

# Wow #8 — visit completion mix for MOON-2026 (pie).
VISIT_SQL = """SELECT v.status, COUNT(*) AS n
FROM app.visits v
JOIN app.patients p ON p.patient_id = v.patient_id
JOIN app.studies st ON st.study_id = p.study_id
WHERE st.code = 'MOON-2026'
GROUP BY v.status
ORDER BY n DESC"""

# Wow #9 — screen-failure rate across MOON-2026 sites (ranked bar).
SCREENFAIL_SITE_SQL = """SELECT s.name,
       ROUND(100.0 * COUNT(*) FILTER (WHERE NOT p.screen_pass) / COUNT(*), 1) AS screen_fail_pct
FROM app.sites s
JOIN app.studies st ON st.study_id = s.study_id
JOIN app.patients p ON p.site_id = s.site_id
WHERE st.code = 'MOON-2026'
GROUP BY s.name
ORDER BY screen_fail_pct DESC"""

HERO_SUMMARY = (
    "Three of your 14 MOON-2026 sites — Toronto, Tokyo, and Boston — are at risk "
    "of missing their Q2 enrollment targets, each with stalled enrollment over "
    "the last 60 days and elevated screen-failure rates. Munich and São Paulo "
    "remain your strongest performers."
)
TREND_SUMMARY = (
    "Toronto, Tokyo, and Boston have effectively stalled — almost no new patients "
    "over the last 60 days — while Munich keeps enrolling steadily. The gap between "
    "the healthy and stalled sites is widening, which is what puts the three at risk."
)
SCREENFAIL_SUMMARY = (
    "Tokyo's screen-failure rate is about 29% (13 of 45 screened patients failed "
    "screening), well above the study average — a key driver of its lagging "
    "enrollment."
)
DEV_SITE_SUMMARY = (
    "Protocol deviations are concentrated at your three at-risk sites: Tokyo (40), "
    "Toronto (37), and Boston (27) account for the large majority, while every "
    "other MOON-2026 site has 6 or fewer — the same sites that are behind on "
    "enrollment are also generating the most deviations."
)
SCATTER_SUMMARY = (
    "There's a clear inverse relationship: the smaller, at-risk sites (Toronto, "
    "Boston, Tokyo) cluster at the top-left with ~29–32% screen-failure rates, "
    "while the larger, on-track sites sit bottom-right around 4–8%. Screening "
    "quality and enrollment volume move together."
)
CUMULATIVE_SUMMARY = (
    "Cumulative MOON-2026 enrollment has grown to 831 randomized patients over the "
    "past year, ramping from a slow start to a steady ~100/month — a healthy "
    "overall trajectory even with the three lagging sites."
)
SEVERITY_SUMMARY = (
    "Of your protocol deviations, most are minor (126), but there are 51 major and "
    "23 critical — the critical slice is the one to watch and is worth routing to "
    "the at-risk sites for review."
)
VISIT_SUMMARY = (
    "MOON-2026 visit completion looks healthy: about 70% completed, ~20% still "
    "scheduled, and ~10% missed — the missed-visit rate is the lever to watch at "
    "the struggling sites."
)
SCREENFAIL_SITE_SUMMARY = (
    "Screen-failure rates cluster at three sites — Toronto (32%), Tokyo (29%), and "
    "Boston (29%) — far above the rest, which sit between 4% and 15%. The same "
    "three at-risk sites are also screening out the most patients."
)

_DEMO = {
    "hero": {
        "sql": HERO_SQL,
        "summary": HERO_SUMMARY,
        "chart": {"type": "bar", "x_field": "pct_of_target", "y_field": "name",
                  "color_field": "status", "title": "Enrollment progress vs. Q2 target"},
        "followups": [
            "Show the 60-day enrollment trend for the at-risk sites",
            "What's driving the screen-failure rate at Tokyo?",
        ],
    },
    "trend": {
        "sql": TREND_SQL,
        "summary": TREND_SUMMARY,
        "chart": {"type": "line", "x_field": "week", "y_field": "enrolled",
                  "color_field": "name", "title": "60-day enrollment — healthy vs. stalled sites"},
        "followups": [
            "Where are my protocol deviations concentrated across MOON-2026 sites?",
            "What's driving the screen-failure rate at Tokyo?",
        ],
    },
    "screenfail": {
        "sql": SCREENFAIL_SQL,
        "summary": SCREENFAIL_SUMMARY,
        "chart": {"type": "bar", "x_field": "screen_pass", "y_field": "patients",
                  "color_field": None, "title": "Tokyo screening outcomes"},
        "followups": [
            "Show screen-failure rates across my MOON-2026 sites.",
            "Where are my protocol deviations concentrated across MOON-2026 sites?",
        ],
    },
    "deviations_site": {
        "sql": DEV_SITE_SQL,
        "summary": DEV_SITE_SUMMARY,
        "chart": {"type": "bar", "x_field": "deviations", "y_field": "name",
                  "color_field": None, "title": "Protocol deviations across MOON-2026 sites"},
        "followups": [
            "Break down protocol deviations by severity.",
            "How do site size and screen-failure rate relate for MOON-2026?",
        ],
    },
    "scatter": {
        "sql": SCATTER_SQL,
        "summary": SCATTER_SUMMARY,
        "chart": {"type": "scatter", "x_field": "enrolled", "y_field": "screen_fail_pct",
                  "color_field": "status", "title": "Site size vs. screen-failure rate (MOON-2026)"},
        "followups": [
            "Show screen-failure rates across my MOON-2026 sites.",
            "Where are my protocol deviations concentrated across MOON-2026 sites?",
        ],
    },
    "cumulative": {
        "sql": CUMULATIVE_SQL,
        "summary": CUMULATIVE_SUMMARY,
        "chart": {"type": "area", "x_field": "month", "y_field": "cumulative",
                  "color_field": None, "title": "Cumulative enrollment — MOON-2026"},
        "followups": [
            "Which of my MOON-2026 sites are at risk of missing enrollment targets, and what's the 60-day trend?",
            "Where are my protocol deviations concentrated across MOON-2026 sites?",
        ],
    },
    "severity": {
        "sql": SEVERITY_SQL,
        "summary": SEVERITY_SUMMARY,
        "chart": {"type": "donut", "x_field": "n", "y_field": "severity",
                  "color_field": "severity", "title": "Protocol deviations by severity"},
        "followups": [
            "Where are my protocol deviations concentrated across MOON-2026 sites?",
            "What's the visit completion mix for MOON-2026?",
        ],
    },
    "visit": {
        "sql": VISIT_SQL,
        "summary": VISIT_SUMMARY,
        "chart": {"type": "pie", "x_field": "n", "y_field": "status",
                  "color_field": "status", "title": "Visit completion mix — MOON-2026"},
        "followups": [
            "Break down protocol deviations by severity.",
            "Show cumulative enrollment over the past year for MOON-2026.",
        ],
    },
    "screenfail_site": {
        "sql": SCREENFAIL_SITE_SQL,
        "summary": SCREENFAIL_SITE_SUMMARY,
        "chart": {"type": "bar", "x_field": "screen_fail_pct", "y_field": "name",
                  "color_field": None, "title": "Screen-failure rate by MOON-2026 site"},
        "followups": [
            "How do site size and screen-failure rate relate for MOON-2026?",
            "Where are my protocol deviations concentrated across MOON-2026 sites?",
        ],
    },
}


def detect_demo_key(question: str, history: list[dict[str, Any]] | None = None) -> Optional[Any]:
    """Route a question to a scripted wow key (or a refine), else None."""
    q = question.lower()
    # Hero first — its phrasing also mentions "60-day trend", which must NOT
    # divert it to the trend follow-up.
    if "moon-2026" in q and "risk" in q:
        return "hero"
    if "60-day" in q and "trend" in q and ("at-risk" in q or "at risk" in q):
        return "trend"
    if "trend" in q and ("at-risk" in q or "at risk" in q):
        return "trend"
    # screen-failure family — order matters (scatter & Tokyo before the by-site bar).
    if ("site size" in q or "site-size" in q or "relate" in q) and "screen" in q:
        return "scatter"
    if "screen" in q and "tokyo" in q:
        return "screenfail"
    if "screen-failure" in q and ("across" in q or "highest" in q or ("moon" in q and "site" in q)):
        return "screenfail_site"
    if "deviation" in q and "severity" in q:
        return "severity"
    if "deviation" in q and ("concentrat" in q or "across" in q or "by site" in q or "each" in q):
        return "deviations_site"
    if "cumulative" in q and "enrol" in q:
        return "cumulative"
    if "visit" in q and ("completion" in q or "mix" in q or "status" in q):
        return "visit"
    if "at risk" in q and ("site" in q or "enrol" in q):
        return "hero"
    # Refinement: "what about <Site>?" referencing prior context.
    if history:
        m = re.search(r"what about ([a-zà-ú .]+)\??$", q)
        if m:
            site = _match_site(m.group(1).strip())
            if site:
                return ("refine", site)
    return None


def _match_site(fragment: str) -> Optional[str]:
    frag = fragment.strip().strip("?.! ").lower()
    for site in KNOWN_SITES:
        if site.lower() == frag or site.lower() in frag:
            # Normalize Sao Paulo -> São Paulo
            return "São Paulo" if site.lower() in ("sao paulo", "são paulo") else site
    return None


def refine_sql(site: str) -> str:
    safe = site.replace("'", "''")
    return f"""SELECT s.name, s.country,
       COUNT(p.patient_id) AS enrolled,
       s.target_enrollment,
       ROUND(100.0 * COUNT(p.patient_id) / s.target_enrollment) AS pct_of_target
FROM app.sites s
JOIN app.patients p ON p.site_id = s.site_id
WHERE s.name = '{safe}'
GROUP BY s.site_id, s.name, s.country, s.target_enrollment"""


# --- presentation fast-path ----------------------------------------------------

_CHART_WORDS = {
    "bar": "bar", "line": "line", "pie": "pie", "scatter": "scatter",
    "area": "area", "table": "none",
}


def detect_presentation_change(question: str) -> Optional[str]:
    """If the question is a pure 'show as <chart>' request, return the chart type."""
    q = question.lower()
    triggers = ("show me as", "show as", "make it a", "as a ", "render as", "view as")
    if not any(t in q for t in triggers):
        # also bare "as a pie chart"
        if not re.search(r"\bas an? (bar|line|pie|scatter|area|table)", q):
            return None
    for word, ctype in _CHART_WORDS.items():
        if re.search(rf"\b{word}\b", q):
            return ctype
    return None


# --- relevance gate (off-domain decline) ---------------------------------------

OFF_DOMAIN_MSG = "I can only answer questions about your clinical trial operations data."
GENERIC_DECLINE_MSG = (
    "I can't answer that from the data I have. I can help with enrollment, sites, "
    "visits, deviations, screen-failure rates, and study-team activity."
)

# Plain vocabulary that signals a clinical-operations question.
DOMAIN_TERMS = {
    "study", "studies", "trial", "protocol", "site", "patient", "enroll", "enrolment",
    "enrollment", "randomi", "screen", "consent", "visit", "deviation", "investigator",
    "sponsor", "login", "session", "engagement", "adoption", "user", "country", "target",
    "velocity", "risk", "therapeutic", "phase", "q2", "moon", "sunrise", "orion",
    "pegasus", "atlas", "trend", "recruit", "subject",
}
REFINEMENT_WORDS = ("what about", "compare", "that ", "those", "them", "instead", "as a ")


def is_in_domain(question: str, has_history: bool = False) -> bool:
    """Lightweight relevance check — keeps clearly off-domain questions out of the
    SQL pipeline. Site names and (with history) refinement phrasings count."""
    q = question.lower()
    if any(term in q for term in DOMAIN_TERMS):
        return True
    if any(site.lower() in q for site in KNOWN_SITES):
        return True
    if has_history and any(w in q for w in REFINEMENT_WORDS):
        return True
    return False


# --- answerability (hallucinated / absent field decline) -----------------------

# Common clinical fields we deliberately don't model — asking for these declines.
ABSENT_FIELDS = [
    "age", "gender", "sex", "weight", "height", "bmi", "race", "ethnicity",
    "date of birth", "birthdate", "birth date", "dob", "mortality", "death",
    "adverse event", "blood pressure", "dosage", "lab value", "biomarker",
    "diagnosis", "medication", "salary", "revenue", "cost", "ethnic",
]


def answerability_decline(question: str) -> Optional[str]:
    """If the question asks for a field that doesn't exist in the schema, return a
    polite decline naming the field; otherwise None."""
    q = question.lower()
    for term in ABSENT_FIELDS:
        if re.search(rf"\b{re.escape(term)}\b", q):
            article = "an" if term[0] in "aeiou" else "a"
            return (
                f"I don't have {article} '{term}' field in your data. I can answer "
                "questions about enrollment, sites, visits, deviations, "
                "screen-failure rates, and study-team activity."
            )
    return None


# --- heuristic fallback --------------------------------------------------------

_TABLE_HINTS = [
    (("deviation",), "deviations"),
    (("site",), "sites"),
    (("study", "studies", "trial", "protocol"), "studies"),
    (("investigator", "pi "), "investigators"),
    (("visit",), "visits"),
    (("login", "session", "engagement", "adoption"), "user_sessions"),
    (("user", "team"), "study_users"),
    (("patient", "enroll", "screen", "consent", "randomi", "target", "subject", "recruit"), "patients"),
]

_TABLE_ENTITY = {
    "studies": "studies", "sites": "sites", "investigators": "investigators",
    "patients": "patient records", "visits": "visits", "deviations": "protocol deviations",
    "study_users": "study-team users", "user_sessions": "login sessions",
}


def heuristic_table(question: str) -> Optional[str]:
    q = question.lower()
    for keywords, tbl in _TABLE_HINTS:
        if any(k in q for k in keywords) and tbl in allowed_tables():
            return tbl
    return None


def heuristic_sql(question: str) -> Optional[str]:
    """Best-effort listing query for an in-domain question that maps to a table.
    Returns None when no table maps (the caller declines gracefully)."""
    table = heuristic_table(question)
    if table is None:
        return None
    return f"SELECT * FROM app.{table} t LIMIT 100"


def _table_from_sql(sql: str) -> Optional[str]:
    m = re.search(r"from\s+app\.(\w+)", sql or "", re.IGNORECASE)
    return m.group(1) if m else None


def heuristic_summary(question: str, rows: list[dict[str, Any]], sql: str = "") -> dict[str, Any]:
    n = len(rows)
    is_aggregate = "group by" in (sql or "").lower()
    entity = _TABLE_ENTITY.get(_table_from_sql(sql) or "", "matching records")
    if n == 0:
        summary = f"I found no {entity} matching that."
    elif is_aggregate:
        # Grouped result — don't mislabel the row count as the base entity.
        summary = f"Here's the breakdown below ({n} {'row' if n == 1 else 'rows'})."
    else:
        verb = "is" if n == 1 else "are"
        capped = " (showing the first 100)" if n >= 100 else ""
        summary = f"Here {verb} {n} {entity} from your data{capped}."
    # Unscripted listings render as a clean table — never a guessed (and often
    # degenerate) bar over plumbing columns. The scripted arc has explicit charts.
    chart: dict[str, Any] = {"type": "none", "title": entity.title()}
    return {
        "summary": summary,
        "chart": chart,
        "followups": ["Show this as a bar chart", "Break this down by country"],
    }


def demo_payload(key: str) -> dict[str, Any]:
    return _DEMO[key]


# --- safe-extras: curated SQL so the FAKE heuristic answers them respectably
# (real aggregates / filters -> clean table) for local rehearsal without Azure.
# No tenant filter (the validator injects it). Keyed by exact question text. ----
SAFE_EXTRA_SQL: dict[str, str] = {
    "What's the average screen-failure rate by country?":
        "SELECT s.country, ROUND(100.0 * COUNT(*) FILTER (WHERE NOT p.screen_pass) / COUNT(*), 1) AS screen_fail_pct "
        "FROM app.patients p JOIN app.sites s ON s.site_id = p.site_id GROUP BY s.country ORDER BY screen_fail_pct DESC",
    "How many enrolled patients are in each study?":
        "SELECT st.code, COUNT(p.patient_id) AS enrolled FROM app.studies st "
        "LEFT JOIN app.patients p ON p.study_id = st.study_id GROUP BY st.code ORDER BY enrolled DESC",
    "Which sites have the most protocol deviations?":
        "SELECT s.name, COUNT(d.deviation_id) AS deviations FROM app.sites s "
        "JOIN app.deviations d ON d.site_id = s.site_id GROUP BY s.name ORDER BY deviations DESC LIMIT 10",
    "How many visits were completed versus missed?":
        "SELECT v.status, COUNT(*) AS n FROM app.visits v GROUP BY v.status ORDER BY n DESC",
    "List all sites in Germany.":
        "SELECT s.site_id, s.name, s.country, s.target_enrollment FROM app.sites s "
        "WHERE s.country = 'DE' ORDER BY s.name",
    "Which investigators specialize in Oncology?":
        "SELECT i.name, s.name AS site, s.country FROM app.investigators i "
        "JOIN app.sites s ON s.site_id = i.site_id WHERE i.specialization = 'Oncology' ORDER BY s.country",
    "Count sites per country.":
        "SELECT s.country, COUNT(*) AS n_sites FROM app.sites s GROUP BY s.country ORDER BY n_sites DESC",
    "Compare enrolled patients across all studies.":
        "SELECT st.code, COUNT(p.patient_id) AS enrolled FROM app.studies st "
        "LEFT JOIN app.patients p ON p.study_id = st.study_id GROUP BY st.code ORDER BY enrolled DESC",
    "How many investigators are assigned per study?":
        "SELECT st.code, COUNT(i.inv_id) AS investigators FROM app.studies st "
        "JOIN app.sites s ON s.study_id = st.study_id JOIN app.investigators i ON i.site_id = s.site_id "
        "GROUP BY st.code ORDER BY investigators DESC",
    "How many patients consented versus were randomized?":
        "SELECT COUNT(*) FILTER (WHERE p.consent_date IS NOT NULL) AS consented, "
        "COUNT(*) FILTER (WHERE p.randomized) AS randomized FROM app.patients p",
}


def safe_extra_sql(question: str) -> Optional[str]:
    return SAFE_EXTRA_SQL.get(question.strip())
