from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

from app.core.config import ROOT


DEFAULT_LOG_PATH = ROOT / "data" / "token-lens.log"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5


def configure_logging(config: dict | None = None, *, force: bool = False) -> Path:
    config = config or {}
    log_path = _resolve_path(config.get("log_file") or config.get("logging_file") or DEFAULT_LOG_PATH)
    max_bytes = _safe_int(config.get("log_max_bytes"), DEFAULT_MAX_BYTES, 1024)
    backup_count = _safe_int(config.get("log_backup_count"), DEFAULT_BACKUP_COUNT, 0)
    level_name = str(config.get("log_level") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    if root_logger.handlers and not force:
        return log_path

    log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] [pid=%(process)d thread=%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S%z",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    handlers: list[logging.Handler] = [file_handler]
    if sys.stderr is not None:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.WARNING)
        handlers.append(stream_handler)

    remote_handler, remote_error = _build_ai_logger_handler(level)
    if remote_handler is not None:
        handlers.append(remote_handler)

    logging.basicConfig(level=level, handlers=handlers, force=force)
    logger = logging.getLogger("token_lens")
    logger.info(
        "logging configured path=%s level=%s max_bytes=%s backup_count=%s",
        log_path,
        logging.getLevelName(level),
        max_bytes,
        backup_count,
    )
    if remote_error:
        logger.warning("ai_logger client disabled reason=%s", remote_error)
    elif remote_handler is not None:
        logger.info(
            "ai_logger client enabled project=%s service=%s environment=%s",
            os.environ.get("AI_LOGGER_PROJECT"),
            os.environ.get("AI_LOGGER_SERVICE"),
            os.environ.get("AI_LOGGER_ENVIRONMENT"),
        )
    return log_path


def _build_ai_logger_handler(level: int) -> tuple[logging.Handler | None, str | None]:
    if not str(os.environ.get("AI_LOGGER_SERVER_URL") or "").strip():
        return None, None
    try:
        from ai_logger import configured_logging_handler

        handler = configured_logging_handler()
        handler.setLevel(level)
        return handler, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _resolve_path(value) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def _safe_int(value, default: int, minimum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(number, minimum)
