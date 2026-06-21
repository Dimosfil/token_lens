from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import threading
import time

from app.core.types import ImportStats
from app.services.import_service import import_codex_logs, import_opencode_sources


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

        errors = []
        codex_stats = ImportStats()
        opencode_stats = ImportStats()
        try:
            codex_stats = import_codex_logs()
        except Exception as exc:
            errors.append(f"codex: {type(exc).__name__}: {exc}")
            LOGGER.exception("codex import failed")

        try:
            opencode_stats = import_opencode_sources()
        except Exception as exc:
            errors.append(f"opencode: {type(exc).__name__}: {exc}")
            LOGGER.exception("opencode import failed")

        stats = ImportStats(
            scanned=codex_stats.scanned + opencode_stats.scanned,
            imported=codex_stats.imported + opencode_stats.imported,
            skipped=codex_stats.skipped + opencode_stats.skipped,
            archived=codex_stats.archived + opencode_stats.archived,
        )
        duration = round(time.monotonic() - start, 3)
        with STATE_LOCK:
            IMPORT_STATE.status = "failed" if errors else "succeeded"
            IMPORT_STATE.completed_at = _utc_now()
            IMPORT_STATE.duration_seconds = duration
            IMPORT_STATE.stats = stats.__dict__
            IMPORT_STATE.error = "; ".join(errors) if errors else None
        if errors:
            LOGGER.error(
                "import failed duration_seconds=%s scanned=%s imported=%s skipped=%s archived=%s errors=%s",
                duration,
                stats.scanned,
                stats.imported,
                stats.skipped,
                stats.archived,
                "; ".join(errors),
            )
            raise RuntimeError("; ".join(errors))
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
