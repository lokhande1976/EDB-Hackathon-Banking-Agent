# ── Stage 1: Build banking React frontend ───────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Build automation UI React frontend ──────────────────────────
FROM node:20-slim AS automation-ui-builder
WORKDIR /automation_ui
COPY automation_ui/package.json ./
RUN npm install
COPY automation_ui/ ./
RUN npm run build

# ── Stage 3: Python ADK application ─────────────────────────────────────
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
COPY automation_agent ./automation_agent/

# Copy SQLite database (local fallback when BQ_DATASET is empty)
COPY bank_data.db ./

# Copy built React frontends
COPY --from=frontend-builder /frontend/dist ./frontend/dist/
COPY --from=automation-ui-builder /automation_ui/dist ./automation_ui/dist/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
