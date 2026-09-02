FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml uv.lock ./
COPY SystemCode/api/pyproject.toml SystemCode/api/pyproject.toml
COPY SystemCode/workflows/pyproject.toml SystemCode/workflows/pyproject.toml
COPY SystemCode/data-crawler/pyproject.toml SystemCode/data-crawler/pyproject.toml
COPY SystemCode/data-preparation/pyproject.toml SystemCode/data-preparation/pyproject.toml
RUN uv sync --frozen --no-dev --package foodie-data-preparation --no-install-workspace

COPY SystemCode/data-preparation SystemCode/data-preparation
RUN uv sync --frozen --no-dev --package foodie-data-preparation

CMD ["uv", "run", "--frozen", "--no-dev", "--package", "foodie-data-preparation", "dbt", "build", "--project-dir", "SystemCode/data-preparation"]
