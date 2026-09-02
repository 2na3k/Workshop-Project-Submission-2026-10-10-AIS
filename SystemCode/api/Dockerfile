FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1

# Copy dependency metadata first so Docker can cache dependency installation.
COPY pyproject.toml uv.lock ./
COPY SystemCode/api/pyproject.toml SystemCode/api/pyproject.toml
COPY SystemCode/workflows/pyproject.toml SystemCode/workflows/pyproject.toml
COPY SystemCode/data-crawler/pyproject.toml SystemCode/data-crawler/pyproject.toml
COPY SystemCode/data-preparation/pyproject.toml SystemCode/data-preparation/pyproject.toml
RUN uv sync --frozen --no-dev --package foodie-api --no-install-workspace

COPY SystemCode/api SystemCode/api
COPY SystemCode/workflows SystemCode/workflows
RUN uv sync --frozen --no-dev --package foodie-api

EXPOSE 8000
CMD ["uv", "run", "--frozen", "--no-dev", "--package", "foodie-api", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
