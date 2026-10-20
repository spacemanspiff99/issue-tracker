FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN useradd --create-home --shell /bin/sh appuser
COPY pyproject.toml README.md /app/
COPY src /app/src
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e ".[dev]"
# Chromium for the browser UAT suite (tests/e2e, RUN_BROWSER_UAT=1 in remote-compose-deploy.sh).
RUN python -m playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*

COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY documentation /app/documentation
COPY tests /app/tests
RUN mkdir -p /app/artifacts && chown appuser /app/artifacts

USER appuser
EXPOSE 8000
CMD ["uvicorn", "issue_tracker.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
