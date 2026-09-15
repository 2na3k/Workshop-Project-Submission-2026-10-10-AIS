FROM python:3.12-slim

# uv resolves the workspace, so the build context is SystemCode/.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY remy/backend/ ./remy/backend/

RUN uv sync --package remy-backend --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "--package", "remy-backend", \
     "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
