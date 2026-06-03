"""
CompetitorLens — FastAPI Backend
================================
Run:  uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db, close_db
from routers import auth, settings, market_analysis, business_analysis, history

cfg = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist
    await init_db()
    yield
    # Shutdown: close DB pool
    await close_db()


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


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": cfg.APP_NAME}


@app.get(f"{PREFIX}/health")
async def api_health():
    return {"status": "ok", "service": cfg.APP_NAME, "version": "1.0.0"}
