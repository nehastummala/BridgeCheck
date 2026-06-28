"""
Database models for BridgeCheck.
Uses SQLAlchemy with SQLite (dev) or PostgreSQL (prod).
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text
from sqlalchemy.sql import func
from .database import Base


class Resource(Base):
    """
    A mental health resource in the BridgeCheck database.
    All list fields (tags, barriers, access_modes, links, why_text)
    are stored as JSON so the schema stays flexible as we add resources.
    """
    __tablename__ = "resources"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    cost_badge  = Column(String(20), nullable=False)   # "free" | "low"
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # JSON arrays / objects
    tags         = Column(JSON, default=list)   # ["therapy","crisis","peer","substance","medication"]
    barriers     = Column(JSON, default=list)   # ["cost","transport","language","privacy","waittime","info"]
    access_modes = Column(JSON, default=list)   # ["inperson","video","phone","text"]
    links        = Column(JSON, default=list)   # [{"label":"Call 988","url":"tel:988","icon":"ti-phone","primary":true}]
    why_text     = Column(JSON, default=dict)   # {"cost": "Free — no insurance required.", "privacy": "Anonymous..."}


class AssessmentLog(Base):
    """
    Anonymous aggregate log — no PII, no session IDs, no IP.
    Stores only aggregate signals for future research.
    One row per completed assessment.
    """
    __tablename__ = "assessment_logs"

    id              = Column(Integer, primary_key=True, index=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Aggregate signals only — nothing identifying
    support_type    = Column(String(50))
    barrier_count   = Column(Integer)
    primary_barrier = Column(String(50))
    access_count    = Column(Integer)
    has_zip         = Column(Boolean, default=False)
    skipped_q3      = Column(Boolean, default=False)
    confidence      = Column(Integer)
    top_match_id    = Column(Integer)
