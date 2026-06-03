from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import User, Analysis, Competitor, AnalysisType, AnalysisStatus
from schemas import AnalysisOut, AnalysisDetailOut, AnalysisListOut, HistoryStatsOut, CompetitorOut, AnalysisSaveRequest
from routers.auth import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


@router.post("/save", response_model=AnalysisOut)
async def save_analysis(
    body: AnalysisSaveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = body.payload
    if payload.error:
        raise HTTPException(status_code=400, detail=payload.error)

    payload_data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()

    analysis = Analysis(
        user_id=user.id,
        title=body.title,
        subtitle=body.subtitle,
        analysis_type=body.analysis_type,
        status=AnalysisStatus.COMPLETED,
        industry=body.industry,
        country=body.country,
        google_maps_url=body.google_maps_url,
        max_reviews=body.max_reviews,
        analysis_depth=body.analysis_depth,
        result_data=payload_data,
        token_usage={"total_tokens": payload.allTokensUsed},
        completed_at=datetime.utcnow(),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    competitors = payload.competitorsAnalyzed or []
    details = payload.competitorsDetails or []
    for idx, comp in enumerate(competitors):
        detail = details[idx] if idx < len(details) else {}
        positive_pct = comp.get("positivePercentage", 0) or 0
        negative_pct = comp.get("negativePercentage", 0) or 0
        neutral_pct = 100 - positive_pct - negative_pct

        record = Competitor(
            analysis_id=analysis.id,
            name=comp.get("name", ""),
            address=detail.get("address", ""),
            google_maps_url=detail.get("googleMaps", ""),
            google_rating=comp.get("googleRating", 0) or 0,
            total_reviews=comp.get("reviewsAnalyzed", 0) or 0,
            positive_pct=positive_pct,
            negative_pct=negative_pct,
            neutral_pct=neutral_pct,
            avg_polarity=comp.get("avgSentiment", 0) or 0,
            gm_reviews_count=comp.get("googleMapsReviewsCount", 0) or 0,
            trustpilot_url=detail.get("trustpilotUrl", ""),
            trustpilot_rating=detail.get("trustpilotRating") or None,
            trust_score=detail.get("trustScore") or None,
            trustpilot_reviews_count=detail.get("trustpilotReviewsCount", 0) or 0,
            ai_insights=detail.get("aiInsights", ""),
        )
        db.add(record)

    await db.commit()
    return AnalysisOut.model_validate(analysis)


@router.get("", response_model=AnalysisListOut)
async def list_analyses(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
    analysis_type: Optional[str] = Query(None, description="MARKET or SINGLE"),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Analysis).where(Analysis.user_id == user.id)

    if analysis_type and analysis_type.upper() in ("MARKET", "SINGLE"):
        query = query.where(Analysis.analysis_type == AnalysisType(analysis_type.upper()))
    if search:
        query = query.where(Analysis.title.ilike(f"%{search}%"))
    if date_from:
        query = query.where(Analysis.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        dt = datetime.fromisoformat(date_to) + timedelta(days=1)
        query = query.where(Analysis.created_at < dt)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    total_pages = math.ceil(total / per_page) if total else 1

    # Fetch page
    query = query.order_by(desc(Analysis.created_at)).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = [AnalysisOut.model_validate(r) for r in result.scalars().all()]

    return AnalysisListOut(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=HistoryStatsOut)
async def history_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(Analysis).where(Analysis.user_id == user.id)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_q = base.where(Analysis.created_at >= month_start)
    this_month = (await db.execute(select(func.count()).select_from(this_month_q.subquery()))).scalar() or 0

    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
    prev_month_q = base.where(
        and_(Analysis.created_at >= prev_month_start, Analysis.created_at < month_start)
    )
    prev_month = (await db.execute(select(func.count()).select_from(prev_month_q.subquery()))).scalar() or 0
    growth = ((this_month - prev_month) / max(prev_month, 1)) * 100

    comp_count_q = (
        select(func.count())
        .select_from(Competitor)
        .join(Analysis)
        .where(Analysis.user_id == user.id)
    )
    total_comps = (await db.execute(comp_count_q)).scalar() or 0

    processing_q = base.where(Analysis.status == AnalysisStatus.PROCESSING)
    active = (await db.execute(select(func.count()).select_from(processing_q.subquery()))).scalar() or 0

    return HistoryStatsOut(
        total_reports=total,
        total_this_month=this_month,
        growth_pct=round(growth, 1),
        total_competitors_analyzed=total_comps,
        active_monitoring=active,
    )


@router.get("/{analysis_id}", response_model=AnalysisDetailOut)
async def get_analysis(
    analysis_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .where(Analysis.id == analysis_id, Analysis.user_id == user.id)
        .options(selectinload(Analysis.competitors))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisDetailOut.model_validate(analysis)


@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    await db.delete(analysis)
    await db.commit()
    return {"detail": "Analysis deleted"}
