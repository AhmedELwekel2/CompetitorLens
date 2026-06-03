#!/usr/bin/env bash
# CompetitorLens Backend — Quick start
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "╔══════════════════════════════════════════╗"
echo "║   CompetitorLens — Backend Starter       ║"
echo "╚══════════════════════════════════════════╝"

# ── Option 1: Docker (recommended) ──────────────────────────────────
if [ "$1" = "docker" ]; then
    echo "→ Starting with Docker Compose..."
    docker compose up --build -d
    echo "✓ PostgreSQL running on :5432"
    echo "✓ FastAPI running on :8000"
    echo "→ Run 'docker compose logs -f backend' to view logs"
    exit 0
fi

# ── Option 2: Local dev ─────────────────────────────────────────────
echo "→ Starting local dev server..."

# Check .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "✗ Missing backend/.env — copy from .env.example and fill in values"
    exit 1
fi

# Activate venv if not active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d "$SCRIPT_DIR/.venv" ]; then
        echo "→ Creating virtual environment..."
        python3 -m venv "$SCRIPT_DIR/.venv"
    fi
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Install deps
echo "→ Installing Python dependencies..."
pip install -r "$BACKEND_DIR/requirements.txt" -q

# Start
echo "→ Starting FastAPI on http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
cd "$BACKEND_DIR"
exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
