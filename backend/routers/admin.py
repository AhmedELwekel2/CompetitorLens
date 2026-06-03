"""
Admin dashboard endpoints — manage users (approve, reject, deactivate, etc.)
"""

import json
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserRole, UserStatus, Analysis, AnalysisStatus
from schemas import AdminUserOut, AdminUserUpdate, AdminUserList
from routers.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserList)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status: UserStatus | None = None,
    role: UserRole | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional filters (admin only)."""
    query = select(User)
    count_query = select(func.count(User.id))

    # Filters
    if search:
        like = f"%{search}%"
        filter_clause = or_(User.full_name.ilike(like), User.email.ilike(like))
        query = query.where(filter_clause)
        count_query = count_query.where(filter_clause)
    if status:
        query = query.where(User.status == status)
        count_query = count_query.where(User.status == status)
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    # Count
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, ceil(total / per_page))

    # Paginate
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()

    return AdminUserList(
        items=[AdminUserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a single user's details (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return AdminUserOut.model_validate(user)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's status, role, or active state (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from deactivating/demoting themselves
    if user.id == admin.id and body.role == UserRole.USER:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    if body.status is not None:
        user.status = body.status
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.commit()
    await db.refresh(user)
    return AdminUserOut.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (admin only)."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()


@router.get("/stats")
async def admin_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard statistics (admin only)."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    pending_users = (await db.execute(
        select(func.count(User.id)).where(User.status == UserStatus.PENDING)
    )).scalar() or 0
    approved_users = (await db.execute(
        select(func.count(User.id)).where(User.status == UserStatus.APPROVED)
    )).scalar() or 0
    rejected_users = (await db.execute(
        select(func.count(User.id)).where(User.status == UserStatus.REJECTED)
    )).scalar() or 0
    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar() or 0

    # System-wide analysis stats
    total_analyses = (await db.execute(select(func.count(Analysis.id)))).scalar() or 0
    completed_analyses = (await db.execute(
        select(func.count(Analysis.id)).where(Analysis.status == AnalysisStatus.COMPLETED)
    )).scalar() or 0
    failed_analyses = (await db.execute(
        select(func.count(Analysis.id)).where(Analysis.status == AnalysisStatus.FAILED)
    )).scalar() or 0

    # Total tokens across all analyses
    all_analyses = (await db.execute(
        select(Analysis.token_usage).where(Analysis.token_usage.isnot(None))
    )).scalars().all()
    total_tokens = 0
    for tu in all_analyses:
        if isinstance(tu, dict):
            total_tokens += tu.get("total_tokens", 0) or 0
        elif isinstance(tu, str):
            try:
                parsed = json.loads(tu)
                total_tokens += parsed.get("total_tokens", 0) or 0
            except Exception:
                pass

    # Estimated cost (GPT-4o: ~$5/1M input, ~$15/1M output — avg ~$10/1M tokens)
    estimated_cost = round(total_tokens * 10.0 / 1_000_000, 2)

    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "approved_users": approved_users,
        "rejected_users": rejected_users,
        "active_users": active_users,
        "total_analyses": total_analyses,
        "completed_analyses": completed_analyses,
        "failed_analyses": failed_analyses,
        "total_tokens": total_tokens,
        "estimated_cost": estimated_cost,
    }


@router.get("/user-usage")
async def user_usage_list(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get usage stats for every user (admin only). Returns a list of {user_id, stats}."""
    # Get all users
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    user_ids = [u.id for u in users]

    if not user_ids:
        return []

    # Aggregate analyses per user
    analyses_counts = await db.execute(
        select(
            Analysis.user_id,
            func.count(Analysis.id).label("total_analyses"),
            func.count(case((Analysis.status == AnalysisStatus.COMPLETED, 1))).label("completed_analyses"),
            func.count(case((Analysis.status == AnalysisStatus.FAILED, 1))).label("failed_analyses"),
            func.max(Analysis.created_at).label("last_activity"),
        )
        .where(Analysis.user_id.in_(user_ids))
        .group_by(Analysis.user_id)
    )
    count_rows = {row.user_id: row for row in analyses_counts.all()}

    # Token usage per user
    token_rows = await db.execute(
        select(Analysis.user_id, Analysis.token_usage)
        .where(Analysis.user_id.in_(user_ids))
        .where(Analysis.token_usage.isnot(None))
    )

    tokens_per_user: dict = {}
    for row in token_rows.all():
        uid = row.user_id
        tu = row.token_usage
        tokens = 0
        if isinstance(tu, dict):
            tokens = tu.get("total_tokens", 0) or 0
        elif isinstance(tu, str):
            try:
                tokens = json.loads(tu).get("total_tokens", 0) or 0
            except Exception:
                pass
        tokens_per_user[uid] = tokens_per_user.get(uid, 0) + tokens

    # Build response
    usage_list = []
    for u in users:
        counts = count_rows.get(u.id)
        total_tokens = tokens_per_user.get(u.id, 0)
        estimated_cost = round(total_tokens * 10.0 / 1_000_000, 2)

        usage_list.append({
            "user_id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
            "avatar_initials": u.avatar_initials,
            "status": u.status.value if u.status else "PENDING",
            "role": u.role.value if u.role else "USER",
            "is_active": u.is_active,
            "total_analyses": counts.total_analyses if counts else 0,
            "completed_analyses": counts.completed_analyses if counts else 0,
            "failed_analyses": counts.failed_analyses if counts else 0,
            "total_tokens": total_tokens,
            "estimated_cost": estimated_cost,
            "last_activity": counts.last_activity.isoformat() if counts and counts.last_activity else None,
        })

    return usage_list


@router.get("/users/{user_id}/usage")
async def user_usage_detail(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed usage for a specific user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Analysis stats
    stats = (await db.execute(
        select(
            func.count(Analysis.id).label("total"),
            func.count(case((Analysis.status == AnalysisStatus.COMPLETED, 1))).label("completed"),
            func.count(case((Analysis.status == AnalysisStatus.FAILED, 1))).label("failed"),
            func.count(case((Analysis.status == AnalysisStatus.PROCESSING, 1))).label("processing"),
            func.max(Analysis.created_at).label("last_activity"),
        )
        .where(Analysis.user_id == user_id)
    )).one()

    # Token aggregation
    token_rows = await db.execute(
        select(Analysis.token_usage, Analysis.created_at)
        .where(Analysis.user_id == user_id)
        .where(Analysis.token_usage.isnot(None))
        .order_by(Analysis.created_at.desc())
    )

    total_tokens = 0
    usage_over_time = []
    for row in token_rows.all():
        tu = row.token_usage
        tokens = 0
        if isinstance(tu, dict):
            tokens = tu.get("total_tokens", 0) or 0
        elif isinstance(tu, str):
            try:
                tokens = json.loads(tu).get("total_tokens", 0) or 0
            except Exception:
                pass
        total_tokens += tokens
        if tokens > 0:
            usage_over_time.append({
                "date": row.created_at.isoformat() if row.created_at else None,
                "tokens": tokens,
            })

    # Recent analyses
    recent = (await db.execute(
        select(Analysis)
        .where(Analysis.user_id == user_id)
        .order_by(Analysis.created_at.desc())
        .limit(10)
    )).scalars().all()

    recent_analyses = []
    for a in recent:
        tu = a.token_usage or {}
        if isinstance(tu, str):
            try:
                tu = json.loads(tu)
            except Exception:
                tu = {}
        recent_analyses.append({
            "id": str(a.id),
            "title": a.title,
            "analysis_type": a.analysis_type.value if a.analysis_type else None,
            "status": a.status.value if a.status else None,
            "tokens": (tu.get("total_tokens", 0) or 0) if isinstance(tu, dict) else 0,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        })

    estimated_cost = round(total_tokens * 10.0 / 1_000_000, 2)

    return {
        "user_id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "status": user.status.value if user.status else "PENDING",
        "role": user.role.value if user.role else "USER",
        "total_analyses": stats.total,
        "completed_analyses": stats.completed,
        "failed_analyses": stats.failed,
        "processing_analyses": stats.processing,
        "total_tokens": total_tokens,
        "estimated_cost": estimated_cost,
        "last_activity": stats.last_activity.isoformat() if stats.last_activity else None,
        "recent_analyses": recent_analyses,
        "usage_over_time": usage_over_time[:30],
    }
