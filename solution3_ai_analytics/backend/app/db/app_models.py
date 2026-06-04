"""Clinical-operations tables in the `app` schema (B7).

Every table carries a denormalized `sponsor_id` so the Phase 2 tenant-filter
injection on the anchor table is always correct. FKs + indexes on common join
columns (site_id, study_id, patient_id, sponsor_id).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

SCHEMA = "app"


class Study(Base):
    __tablename__ = "studies"
    __table_args__ = {"schema": SCHEMA}

    study_id: Mapped[int] = mapped_column(primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    phase: Mapped[str] = mapped_column(String(16))
    therapeutic_area: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[dt.date] = mapped_column(Date)


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (
        Index("ix_sites_study_id", "study_id"),
        Index("ix_sites_sponsor_id", "sponsor_id"),
        {"schema": SCHEMA},
    )

    site_id: Mapped[int] = mapped_column(primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64))
    study_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.studies.study_id"))
    name: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(8))
    target_enrollment: Mapped[int] = mapped_column(Integer)


class Investigator(Base):
    __tablename__ = "investigators"
    __table_args__ = (
        Index("ix_investigators_site_id", "site_id"),
        Index("ix_investigators_sponsor_id", "sponsor_id"),
        {"schema": SCHEMA},
    )

    inv_id: Mapped[int] = mapped_column(primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64))
    site_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.sites.site_id"))
    name: Mapped[str] = mapped_column(String(128))
    specialization: Mapped[str] = mapped_column(String(64))


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        Index("ix_patients_site_id", "site_id"),
        Index("ix_patients_study_id", "study_id"),
        Index("ix_patients_sponsor_id", "sponsor_id"),
        {"schema": SCHEMA},
    )

    patient_id: Mapped[int] = mapped_column(primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64))
    site_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.sites.site_id"))
    study_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.studies.study_id"))
    consent_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    screen_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    randomized: Mapped[bool] = mapped_column(Boolean, default=False)


class Visit(Base):
    __tablename__ = "visits"
    __table_args__ = (
        Index("ix_visits_patient_id", "patient_id"),
        Index("ix_visits_sponsor_id", "sponsor_id"),
        {"schema": SCHEMA},
    )

    visit_id: Mapped[int] = mapped_column(primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64))
    patient_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.patients.patient_id"))
    planned_date: Mapped[dt.date] = mapped_column(Date)
    actual_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32))


class Deviation(Base):
    __tablename__ = "deviations"
    __table_args__ = (
        Index("ix_deviations_site_id", "site_id"),
        Index("ix_deviations_study_id", "study_id"),
        Index("ix_deviations_sponsor_id", "sponsor_id"),
        {"schema": SCHEMA},
    )

    deviation_id: Mapped[int] = mapped_column(primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64))
    study_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.studies.study_id"))
    site_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.sites.site_id"))
    type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    occurred_date: Mapped[dt.date] = mapped_column(Date)


class StudyUser(Base):
    __tablename__ = "study_users"
    __table_args__ = (
        Index("ix_study_users_sponsor_id", "sponsor_id"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[int] = mapped_column(primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(64))


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_sponsor_id", "sponsor_id"),
        {"schema": SCHEMA},
    )

    session_id: Mapped[int] = mapped_column(primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.study_users.user_id"))
    login_date: Mapped[dt.date] = mapped_column(Date)
    duration_seconds: Mapped[int] = mapped_column(Integer)


class QueryAudit(Base):
    """One row per executed query (written by the execute node, Phase 2)."""

    __tablename__ = "query_audit"
    __table_args__ = {"schema": SCHEMA}

    query_id: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g. q_8f4a2d1c
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    sponsor_id: Mapped[str] = mapped_column(String(64))
    sql: Mapped[str] = mapped_column(Text)
    tables_used: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    latency_ms: Mapped[int] = mapped_column(Integer)
    rows_returned: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
