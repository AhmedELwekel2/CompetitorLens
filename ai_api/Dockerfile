FROM python:3.12-slim

WORKDIR /app

# Install Chrome and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    curl \
    unzip \
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome binary location
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Install Python dependencies
COPY ai_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy AI API source
COPY ai_api/ ./

ENV PYTHONPATH=/app
ENV TRANSFORMERS_NO_TF=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "600", "--workers", "1", "--threads", "4", "app:app"]