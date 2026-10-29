FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

RUN pip install --no-cache-dir uv==0.12.2

COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser alembic ./alembic
RUN uv sync --frozen --no-dev

COPY --chown=appuser:appuser scripts ./scripts
USER appuser

EXPOSE 8000

CMD ["uvicorn", "doctorly.main:app", "--host", "0.0.0.0", "--port", "8000"]
