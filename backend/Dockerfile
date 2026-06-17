# ──────────────────────────────────────────
# Base
# ──────────────────────────────────────────
# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

# Install the project into `/backend`
WORKDIR /backend
# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY ./app/ /backend/app/
COPY pyproject.toml uv.lock /backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

FROM python:3.12-slim-bookworm AS runner

# Setup a non-root user
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy the application from the builder
COPY --from=builder --chown=nonroot:nonroot /backend /backend

# Place executables in the environment at the front of the path
ENV PATH="/backend/.venv/bin:$PATH"
ENV PYTHONPATH="/backend/app/"
ENV PYTHONUNBUFFERED=1

USER nonroot

WORKDIR /backend

# ──────────────────────────────────────────
# Dev — hot reload via volume mount
# ──────────────────────────────────────────
FROM runner AS dev
CMD ["fastapi", "dev", "/backend/app/main.py", "--host", "0.0.0.0", "--port", "8000"]

# ──────────────────────────────────────────
# Prod — no dev deps, no volume mount
# ──────────────────────────────────────────
FROM runner AS prod
CMD ["fastapi", "run", "/backend/app/main.py", "--host", "0.0.0.0", "--port", "8000"]

# ──────────────────────────────────────────
# Worker — prod + playwright chromium
# ──────────────────────────────────────────
FROM runner AS worker
ENV PLAYWRIGHT_BROWSERS_PATH=/home/nonroot/.cache/ms-playwright/
USER root
RUN playwright install chromium --only-shell --with-deps \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
            chromium \
            xorg \
            openbox \
            python3-tk \
            python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && chown -R nonroot:nonroot /home/nonroot/
USER nonroot
CMD ["prefect", "worker", "start", "--pool", "local-pool"]
