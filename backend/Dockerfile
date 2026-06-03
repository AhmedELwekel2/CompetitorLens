FROM python:3.12-slim

WORKDIR /app

# System deps for asyncpg and bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# AI API modules are imported by analysis_service.py
COPY ai_api/ ./ai_api/

# AI API Python dependencies (transformers, selenium, etc.)
RUN pip install --no-cache-dir \
    flask>=3.0.0 flask-cors>=4.0.0 \
    openai>=1.30.0 aiohttp>=3.9.0 \
    transformers>=4.40.0 torch>=2.0.0 \
    pandas>=2.2.0 selenium>=4.20.0 \
    webdriver-manager>=4.0.0 plotly>=5.22.0 \
    python-dotenv>=1.0.0

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]