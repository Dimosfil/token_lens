from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import threading
import time

from app.services.import_service import import_codex_logs


LOGGER = logging.getLogger("token_lens.import")
IMPORT_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()


@dataclass
class ImportRunState:
    status: str = "idle"
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    stats: dict | None = None
    error: str | None = None


IMPORT_STATE = ImportRunState()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def import_status() -> dict:
    with STATE_LOCK:
        return asdict(IMPORT_STATE)


def run_import():
    with IMPORT_LOCK:
        start = time.monotonic()
        LOGGER.info("import started")
        with STATE_LOCK:
            IMPORT_STATE.status = "running"
            IMPORT_STATE.started_at = _utc_now()
            IMPORT_STATE.completed_at = None
            IMPORT_STATE.duration_seconds = None
            IMPORT_STATE.stats = None
            IMPORT_STATE.error = None
        try:
            stats = import_codex_logs()
        except Exception as exc:
            duration = round(time.monotonic() - start, 3)
            with STATE_LOCK:
                IMPORT_STATE.status = "failed"
                IMPORT_STATE.completed_at = _utc_now()
                IMPORT_STATE.duration_seconds = duration
                IMPORT_STATE.error = f"{type(exc).__name__}: {exc}"
            LOGGER.exception("import failed duration_seconds=%s", duration)
            raise
        duration = round(time.monotonic() - start, 3)
        with STATE_LOCK:
            IMPORT_STATE.status = "succeeded"
            IMPORT_STATE.completed_at = _utc_now()
            IMPORT_STATE.duration_seconds = duration
            IMPORT_STATE.stats = stats.__dict__
        LOGGER.info(
            "import succeeded duration_seconds=%s scanned=%s imported=%s skipped=%s archived=%s",
            duration,
            stats.scanned,
            stats.imported,
            stats.skipped,
            stats.archived,
        )
        return stats


def auto_import_loop(interval: int):
    while True:
        try:
            run_import()
        except Exception:
            LOGGER.exception("background import iteration failed")
        time.sleep(interval)
