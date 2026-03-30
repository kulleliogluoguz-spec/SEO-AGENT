FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Copy application code
# Note: In development, this is overridden by volume mount (./apps/api:/app)
COPY . .

EXPOSE 8000

# Default: run API server. Override in docker-compose for worker.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
