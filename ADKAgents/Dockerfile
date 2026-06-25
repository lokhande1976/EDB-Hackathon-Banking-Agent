# ── Stage 1: Build the React frontend ──────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python ADK application ────────────────────────────────────
FROM python:3.14-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies first (layer caching)
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY main.py ./
COPY bank_agent ./bank_agent/

# Copy SQLite database (local fallback when BQ_DATASET is empty)
COPY bank_data.db ./

# Copy built React frontend from Stage 1
COPY --from=frontend-builder /frontend/dist ./frontend/dist/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
