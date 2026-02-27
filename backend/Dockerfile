# ──────────────────────────────────────────
# Base
# ──────────────────────────────────────────
FROM python:3.12-slim AS base
WORKDIR /app
RUN pip install uv --break-system-packages

# ──────────────────────────────────────────
# Dev — hot reload via volume mount
# ──────────────────────────────────────────
FROM base AS dev
COPY pyproject.toml uv.lock ./
RUN uv sync --all-groups
CMD ["uv", "run", "fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]

# ──────────────────────────────────────────
# Prod — no dev deps, no volume mount
# ──────────────────────────────────────────
FROM base AS prod
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev
COPY app/ ./app/
CMD ["uv", "run", "fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
