from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
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
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
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

    logging.basicConfig(level=level, handlers=handlers, force=force)
    logging.getLogger("token_lens").info(
        "logging configured path=%s level=%s max_bytes=%s backup_count=%s",
        log_path,
        logging.getLevelName(level),
        max_bytes,
        backup_count,
    )
    return log_path


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
