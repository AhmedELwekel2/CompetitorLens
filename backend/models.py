import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class AnalysisType(str, enum.Enum):
    MARKET = "MARKET"
    SINGLE = "SINGLE"


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    professional_title = Column(String(255), default="")
    hashed_password = Column(String(255), nullable=False)
    avatar_initials = Column(String(5), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Settings
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    # Analyses
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")


# ─── User Settings ────────────────────────────────────────────────────────────

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # API Keys (encrypted in production)
    google_maps_api_key = Column(Text, default="")
    analysis_bearer_token = Column(Text, default="")

    # Notification prefs
    email_summary_enabled = Column(Boolean, default=True)
    volatility_alerts_enabled = Column(Boolean, default=False)
    api_status_alerts_enabled = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="settings")


# ─── Analysis (History) ──────────────────────────────────────────────────────

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Meta
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500), default="")
    analysis_type = Column(SAEnum(AnalysisType), nullable=False)
    status = Column(SAEnum(AnalysisStatus), default=AnalysisStatus.PENDING)

    # Inputs
    industry = Column(String(255), default="")
    country = Column(String(255), default="")
    google_maps_url = Column(Text, default="")
    max_reviews = Column(Integer, default=100)
    analysis_depth = Column(String(50), default="standard")

    # Results (stored as JSON blobs for flexibility)
    result_data = Column(JSON, default=dict)
    token_usage = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="analyses")
    competitors = relationship("Competitor", back_populates="analysis", cascade="all, delete-orphan")


# ─── Competitor ───────────────────────────────────────────────────────────────

class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(500), nullable=False)
    address = Column(Text, default="")
    google_maps_url = Column(Text, default="")
    google_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)

    # Sentiment
    positive_pct = Column(Float, default=0.0)
    negative_pct = Column(Float, default=0.0)
    neutral_pct = Column(Float, default=0.0)
    avg_polarity = Column(Float, default=0.0)

    # Google Maps reviews count
    gm_reviews_count = Column(Integer, default=0)

    # Trustpilot
    trustpilot_url = Column(Text, default="")
    trustpilot_rating = Column(Float, nullable=True)
    trust_score = Column(Float, nullable=True)
    trustpilot_reviews_count = Column(Integer, default=0)

    # AI insights
    ai_insights = Column(Text, default="")

    # Raw review data
    reviews_data = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="competitors")
