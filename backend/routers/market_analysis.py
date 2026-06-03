from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Analysis, Competitor, AnalysisType, AnalysisStatus
from schemas import MarketAnalysisRequest
from routers.auth import get_current_user
from services.analysis_service import AnalysisService

router = APIRouter(prefix="/market-analysis", tags=["market-analysis"])
service = AnalysisService()


@router.post("/run")
async def run_market_analysis(
    body: MarketAnalysisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Starts a market analysis and streams results via SSE.
    Also persists the analysis record to the database.
    """
    # Create analysis record
    analysis = Analysis(
        user_id=user.id,
        title=f"{body.industry.title()} Industry Analysis - {body.country}",
        subtitle="Market Sentiment Overview",
        analysis_type=AnalysisType.MARKET,
        status=AnalysisStatus.PROCESSING,
        industry=body.industry,
        country=body.country,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    analysis_id = analysis.id

    async def event_stream():
        last_payload = {}
        try:
            async for chunk in service.run_market_analysis(
                industry=body.industry,
                country=body.country,
                max_competitors=body.max_competitors,
                reviews_per_competitor=body.reviews_per_competitor,
            ):
                yield chunk
                # Track last payload for DB persistence
                if chunk.startswith("data: "):
                    import json
                    try:
                        last_payload = json.loads(chunk[6:])
                    except Exception:
                        pass

            # Persist final results to DB
            async with AsyncSession(db.bind) as save_db:
                from sqlalchemy import select
                result = await save_db.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
                record = result.scalar_one_or_none()
                if record:
                    record.status = AnalysisStatus.COMPLETED
                    record.completed_at = datetime.utcnow()
                    record.result_data = last_payload
                    record.token_usage = {"total_tokens": last_payload.get("allTokensUsed", 0)}

                    # Save competitors
                    for comp_data in (last_payload.get("competitorsAnalyzed") or []):
                        comp = Competitor(
                            analysis_id=analysis_id,
                            name=comp_data.get("name", ""),
                            google_rating=comp_data.get("googleRating", 0),
                            total_reviews=comp_data.get("reviewsAnalyzed", 0),
                            positive_pct=comp_data.get("positivePercentage", 0),
                            negative_pct=comp_data.get("negativePercentage", 0),
                            neutral_pct=100 - comp_data.get("positivePercentage", 0) - comp_data.get("negativePercentage", 0),
                            avg_polarity=comp_data.get("avgSentiment", 0),
                        )
                        save_db.add(comp)

                    await save_db.commit()
        except Exception as e:
            # Mark as failed
            async with AsyncSession(db.bind) as save_db:
                from sqlalchemy import select
                result = await save_db.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
                record = result.scalar_one_or_none()
                if record:
                    record.status = AnalysisStatus.FAILED
                    record.result_data = {"error": str(e)}
                    await save_db.commit()

            import json
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
