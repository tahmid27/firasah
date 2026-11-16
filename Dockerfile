# Firasah API image (FastAPI). Build context is the repo root.

# Stage 1: install dependencies into a virtualenv
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies first, so this layer is cached until the lockfile changes
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

# Stage 2: runtime image with only the venv and the code the API imports
FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY main.py ./
COPY api ./api
COPY core ./core
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app

# Cloud Run sets PORT; 8000 matches local development
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
