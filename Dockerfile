# ==============================================================================
# OpenData Sentinel - Production Multi-Stage Dockerfile
# Stage 1: Build React + Vite Frontend
# Stage 2: Python FastAPI Data Science Backend & Static SPA Hosting
# ==============================================================================

# --- Stage 1: Frontend Build ---
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Backend & Runtime ---
FROM python:3.10-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend code, scripts, sample datasets, docs
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY data/sample/ ./data/sample/
COPY docs/ ./docs/

# Create runtime directories for SQLite and uploads
RUN mkdir -p data/raw data/processed

# Copy pre-compiled frontend assets from Stage 1
COPY --from=frontend-builder /build/dist ./frontend/dist

# Seed bundled demonstration datasets into SQLite database
RUN python scripts/seed_database.py

EXPOSE 8000

# Health check to ensure API is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch production server via Uvicorn (binds to $PORT for cloud compatibility)
CMD python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
