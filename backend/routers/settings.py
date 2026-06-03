from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserSettings, Analysis
from schemas import SettingsUpdate, SettingsOut, UsageStatsOut
from routers.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


def _mask(value: str) -> str:
    if not value or len(value) < 8:
        return "••••••••"
    return value[:6] + "..." + value[-4:]


@router.get("", response_model=SettingsOut)
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return SettingsOut(
        google_maps_api_key_masked=_mask(settings.google_maps_api_key),
        analysis_bearer_token_masked=_mask(settings.analysis_bearer_token),
        email_summary_enabled=settings.email_summary_enabled,
        volatility_alerts_enabled=settings.volatility_alerts_enabled,
        api_status_alerts_enabled=settings.api_status_alerts_enabled,
        updated_at=settings.updated_at,
    )


@router.patch("", response_model=SettingsOut)
async def update_settings(
    body: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)

    if body.google_maps_api_key is not None:
        settings.google_maps_api_key = body.google_maps_api_key
    if body.analysis_bearer_token is not None:
        settings.analysis_bearer_token = body.analysis_bearer_token
    if body.email_summary_enabled is not None:
        settings.email_summary_enabled = body.email_summary_enabled
    if body.volatility_alerts_enabled is not None:
        settings.volatility_alerts_enabled = body.volatility_alerts_enabled
    if body.api_status_alerts_enabled is not None:
        settings.api_status_alerts_enabled = body.api_status_alerts_enabled

    await db.commit()
    await db.refresh(settings)

    return SettingsOut(
        google_maps_api_key_masked=_mask(settings.google_maps_api_key),
        analysis_bearer_token_masked=_mask(settings.analysis_bearer_token),
        email_summary_enabled=settings.email_summary_enabled,
        volatility_alerts_enabled=settings.volatility_alerts_enabled,
        api_status_alerts_enabled=settings.api_status_alerts_enabled,
        updated_at=settings.updated_at,
    )


@router.post("/test-connection")
async def test_connection(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()
    has_keys = bool(
        settings
        and settings.google_maps_api_key
        and settings.analysis_bearer_token
    )
    return {
        "status": "connected" if has_keys else "missing_keys",
        "message": "All connections verified" if has_keys else "Please configure your API keys",
    }


# Pricing per 1M tokens for cost estimation
_COST_PER_1M = 0.75  # blended rate (input+output average)


@router.get("/usage", response_model=UsageStatsOut)
async def get_usage_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated token/analysis usage for the current user."""
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Fetch all analyses for counting + token aggregation (Python-side for JSON compat)
    all_q = select(Analysis).where(Analysis.user_id == user.id)
    all_result = await db.execute(all_q)
    all_analyses = all_result.scalars().all()

    total_analyses = len(all_analyses)
    total_tokens = sum(
        (a.token_usage or {}).get("total_tokens", 0) or 0
        for a in all_analyses
    )

    # This month
    month_analyses = [a for a in all_analyses if a.created_at and a.created_at >= month_start]
    analyses_this_month = len(month_analyses)
    tokens_this_month = sum(
        (a.token_usage or {}).get("total_tokens", 0) or 0
        for a in month_analyses
    )

    # Recent usage (last 10 analyses)
    recent_analyses = sorted(all_analyses, key=lambda a: a.created_at or datetime.min, reverse=True)[:10]

    recent_usage = []
    for a in recent_analyses:
        tokens = (a.token_usage or {}).get("total_tokens", 0) or 0
        recent_usage.append({
            "id": str(a.id),
            "title": a.title,
            "type": a.analysis_type.value if a.analysis_type else "",
            "tokens": tokens,
            "cost": round((tokens / 1_000_000) * _COST_PER_1M, 4),
            "created_at": a.created_at.isoformat() if a.created_at else "",
        })

    # Averages
    avg_tokens = round(total_tokens / total_analyses, 1) if total_analyses else 0

    # Limits
    monthly_token_limit = 500_000
    monthly_analysis_limit = 100

    return UsageStatsOut(
        total_tokens=total_tokens,
        tokens_this_month=tokens_this_month,
        total_analyses=total_analyses,
        analyses_this_month=analyses_this_month,
        estimated_cost=round((total_tokens / 1_000_000) * _COST_PER_1M, 2),
        cost_this_month=round((tokens_this_month / 1_000_000) * _COST_PER_1M, 2),
        monthly_token_limit=monthly_token_limit,
        monthly_analysis_limit=monthly_analysis_limit,
        avg_tokens_per_analysis=avg_tokens,
        recent_usage=recent_usage,
    )
