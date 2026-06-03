from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Analysis, Competitor, AnalysisType, AnalysisStatus
from schemas import BusinessAnalysisRequest
from routers.auth import get_current_user
from services.analysis_service import AnalysisService

router = APIRouter(prefix="/business-analysis", tags=["business-analysis"])
service = AnalysisService()


@router.post("/run")
async def run_business_analysis(
    body: BusinessAnalysisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Starts a single-business analysis and streams results via SSE.
    """
    analysis = Analysis(
        user_id=user.id,
        title="Business Sentiment Analysis",
        subtitle="Single Entity Deep-Dive",
        analysis_type=AnalysisType.SINGLE,
        status=AnalysisStatus.PROCESSING,
        google_maps_url=body.google_maps_url,
        max_reviews=body.max_reviews,
        analysis_depth=body.analysis_depth,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    analysis_id = analysis.id

    async def event_stream():
        last_payload = {}
        try:
            async for chunk in service.run_business_analysis(
                google_maps_url=body.google_maps_url,
                max_reviews=body.max_reviews,
                analysis_depth=body.analysis_depth,
            ):
                yield chunk
                if chunk.startswith("data: "):
                    import json
                    try:
                        last_payload = json.loads(chunk[6:])
                    except Exception:
                        pass

            # Persist
            async with AsyncSession(db.bind) as save_db:
                from sqlalchemy import select
                result = await save_db.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
                record = result.scalar_one_or_none()
                if record:
                    title = last_payload.get("analysisTitle") or "Business Analysis"
                    record.title = title
                    record.status = AnalysisStatus.COMPLETED
                    record.completed_at = datetime.utcnow()
                    record.result_data = last_payload
                    record.token_usage = {"total_tokens": last_payload.get("allTokensUsed", 0)}

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
