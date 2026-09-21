FROM python:3.12-slim AS base
WORKDIR /app

# Cài uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependencies trước để tận dụng cache layer
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy source
COPY codebase/ codebase/
COPY tests/ tests/

ENTRYPOINT ["uv", "run", "python", "codebase/cli.py"]
