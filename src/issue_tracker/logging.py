from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from logging import LogRecord
from typing import Any

from issue_tracker.config import Settings

SAFE_EXTRA_FIELDS = {
    "duration_ms",
    "event",
    "method",
    "route",
    "status_code",
}


class JsonFormatter(logging.Formatter):
    def __init__(self, *, app: str, service: str, source: str, environment: str) -> None:
        super().__init__()
        self.app = app
        self.service = service
        self.source = source
        self.environment = environment

    def format(self, record: LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "app": self.app,
            "service": self.service,
            "source": self.source,
            "environment": self.environment,
        }
        for field in sorted(SAFE_EXTRA_FIELDS):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def configure_logging(settings: Settings, *, service: str, source: str = "app-log") -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    if settings.log_format == "text":
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s app=issue-tracker "
                f"service={service} source={source} environment={settings.app_environment} "
                "logger=%(name)s %(message)s"
            )
        )
    else:
        handler.setFormatter(
            JsonFormatter(
                app="issue-tracker",
                service=service,
                source=source,
                environment=settings.app_environment,
            )
        )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for logger_name in ("issue_tracker", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True
        logger.setLevel(level)
