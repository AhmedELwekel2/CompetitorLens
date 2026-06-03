from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from models import AnalysisType, AnalysisStatus


# ─── Auth / User ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    professional_title: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    professional_title: Optional[str] = None
    email: Optional[EmailStr] = None


class UserOut(BaseModel):
    id: UUID
    full_name: str
    email: str
    professional_title: str
    avatar_initials: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Settings ─────────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    google_maps_api_key: Optional[str] = None
    analysis_bearer_token: Optional[str] = None
    email_summary_enabled: Optional[bool] = None
    volatility_alerts_enabled: Optional[bool] = None
    api_status_alerts_enabled: Optional[bool] = None


class SettingsOut(BaseModel):
    google_maps_api_key_masked: str = ""
    analysis_bearer_token_masked: str = ""
    email_summary_enabled: bool = True
    volatility_alerts_enabled: bool = False
    api_status_alerts_enabled: bool = True
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Market Analysis ─────────────────────────────────────────────────────────

class MarketAnalysisRequest(BaseModel):
    industry: str = Field(..., min_length=1, description="Industry or business type")
    country: str = Field(..., min_length=1, description="Country or region")
    max_competitors: int = Field(default=5, ge=1, le=10)
    reviews_per_competitor: int = Field(default=100, ge=10, le=500)


# ─── Business Analysis ───────────────────────────────────────────────────────

class BusinessAnalysisRequest(BaseModel):
    google_maps_url: str = Field(..., min_length=1)
    max_reviews: int = Field(default=100, ge=1, le=500)
    analysis_depth: str = Field(default="standard", pattern="^(standard|sentiment)$")


# ─── Competitor ───────────────────────────────────────────────────────────────

class CompetitorOut(BaseModel):
    id: UUID
    name: str
    address: str
    google_maps_url: str
    google_rating: float
    total_reviews: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    avg_polarity: float
    gm_reviews_count: int
    trustpilot_url: str
    trustpilot_rating: Optional[float]
    trust_score: Optional[float]
    trustpilot_reviews_count: int
    ai_insights: str

    class Config:
        from_attributes = True


# ─── Analysis / History ───────────────────────────────────────────────────────

class AnalysisOut(BaseModel):
    id: UUID
    title: str
    subtitle: str
    analysis_type: AnalysisType
    status: AnalysisStatus
    industry: str
    country: str
    google_maps_url: str
    max_reviews: int
    analysis_depth: str
    result_data: dict
    token_usage: dict
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AnalysisDetailOut(AnalysisOut):
    competitors: list[CompetitorOut] = []


class AnalysisListOut(BaseModel):
    items: list[AnalysisOut]
    total: int
    page: int
    per_page: int
    total_pages: int


class HistoryStatsOut(BaseModel):
    total_reports: int
    total_this_month: int
    growth_pct: float
    total_competitors_analyzed: int
    active_monitoring: int


class UsageStatsOut(BaseModel):
    total_tokens: int = 0
    tokens_this_month: int = 0
    total_analyses: int = 0
    analyses_this_month: int = 0
    estimated_cost: float = 0.0
    cost_this_month: float = 0.0
    monthly_token_limit: int = 500000
    monthly_analysis_limit: int = 100
    avg_tokens_per_analysis: float = 0.0
    recent_usage: list[dict] = []




# ─── SSE streaming payload (matches the existing Flask format) ────────────────

class StreamPayload(BaseModel):
    analysisTitle: Optional[str] = None
    competitorsAnalyzedNumber: Optional[int] = None
    totalReview: Optional[int] = None
    avgGoogleRating: Optional[float] = None
    competitorsAnalyzed: Optional[list[dict]] = None
    pieChart: Optional[dict] = None
    competitorSentimentComparisonChart: Optional[list[dict]] = None
    competitorRating_averageSentiment_chart: Optional[list[dict]] = None
    reviewsAnalyzedPerCompetitor: Optional[list[dict]] = None
    competitorsDetails: Optional[list[dict]] = None
    trustpilotData: Optional[list[dict]] = None
    outputFile: Optional[str] = None
    allTokensUsed: int = 0
    error: Optional[str] = None


class AnalysisSaveRequest(BaseModel):
    analysis_type: AnalysisType
    title: str
    subtitle: str = ""
    industry: str = ""
    country: str = ""
    google_maps_url: str = ""
    max_reviews: int = 100
    analysis_depth: str = "standard"
    payload: StreamPayload
