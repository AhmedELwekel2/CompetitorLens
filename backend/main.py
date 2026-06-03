"""
CompetitorLens — FastAPI Backend
================================
Run:  uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db, close_db, AsyncSessionLocal
from models import User, UserSettings, UserRole, UserStatus
from routers import auth, settings, market_analysis, business_analysis, history, admin
from routers.auth import _hash_password, _initials

cfg = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist
    await init_db()
    # Auto-create admin user if not exists
    await _ensure_admin()
    yield
    # Shutdown: close DB pool
    await close_db()


async def _ensure_admin():
    """Create the default admin user on first startup."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        if result.scalar_one_or_none():
            return  # Admin already exists

        admin = User(
            full_name=cfg.ADMIN_FULL_NAME,
            email=cfg.ADMIN_EMAIL,
            hashed_password=_hash_password(cfg.ADMIN_PASSWORD),
            avatar_initials=_initials(cfg.ADMIN_FULL_NAME),
            role=UserRole.ADMIN,
            status=UserStatus.APPROVED,
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        # Create default settings for admin
        admin_settings = UserSettings(user_id=admin.id)
        db.add(admin_settings)
        await db.commit()
        print(f"✅ Admin user created: {cfg.ADMIN_EMAIL}")


app = FastAPI(
    title=cfg.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
PREFIX = cfg.API_PREFIX   # /api/v1

app.include_router(auth.router,              prefix=PREFIX)
app.include_router(settings.router,          prefix=PREFIX)
app.include_router(market_analysis.router,   prefix=PREFIX)
app.include_router(business_analysis.router, prefix=PREFIX)
app.include_router(history.router,           prefix=PREFIX)
app.include_router(admin.router,             prefix=PREFIX)


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": cfg.APP_NAME}


@app.get(f"{PREFIX}/health")
async def api_health():
    return {"status": "ok", "service": cfg.APP_NAME, "version": "1.0.0"}
