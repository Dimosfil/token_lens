from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import threading
import time
from typing import Callable

from app.core.config import load_config
from app.core.codex_discovery import discover_codex_paths
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
    warnings: list[str] | None = None


IMPORT_STATE = ImportRunState()


def import_status() -> dict:
    with STATE_LOCK:
        return asdict(IMPORT_STATE)


def source_warnings(config: dict | None = None, discovered: dict | None = None) -> list[str]:
    config = config or load_config()
    discovered = discovered or discover_codex_paths()
    warnings: list[str] = []

    configured_logs = str(config.get("codex_logs_db") or "").strip()
    preferred_logs = str(discovered.get("codex_logs_db") or "").strip()
    if (
        configured_logs
        and preferred_logs
        and _existing_file(configured_logs)
        and _existing_file(preferred_logs)
        and not _same_path(configured_logs, preferred_logs)
    ):
        warnings.append(
            "codex_logs_db uses a readable override outside the preferred discovered Codex SQLite source; "
            f"configured={configured_logs}; preferred={preferred_logs}"
        )

    return warnings


def run_import() -> ImportStats:
    with IMPORT_LOCK:
        start = time.monotonic()
        warnings = source_warnings()
        LOGGER.info("import started")
        with STATE_LOCK:
            IMPORT_STATE.status = "running"
            IMPORT_STATE.started_at = _utc_now()
            IMPORT_STATE.completed_at = None
            IMPORT_STATE.duration_seconds = None
            IMPORT_STATE.stats = None
            IMPORT_STATE.error = None
            IMPORT_STATE.warnings = warnings

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
            IMPORT_STATE.warnings = warnings
        if errors:
            LOGGER.error(
                "import failed duration_seconds=%s scanned=%s imported=%s skipped=%s archived=%s warnings=%s errors=%s",
                duration,
                stats.scanned,
                stats.imported,
                stats.skipped,
                stats.archived,
                "; ".join(warnings),
                "; ".join(errors),
            )
            raise RuntimeError("; ".join(errors))
        LOGGER.info(
            "import succeeded duration_seconds=%s scanned=%s imported=%s skipped=%s archived=%s warnings=%s",
            duration,
            stats.scanned,
            stats.imported,
            stats.skipped,
            stats.archived,
            "; ".join(warnings),
        )
        return stats


def run_import_capture() -> dict:
    try:
        stats = run_import()
        return {"stats": stats.__dict__, "error": None, "status": import_status()}
    except RuntimeError as error:
        return {"stats": None, "error": str(error), "status": import_status()}


def refresh_dashboard(load_dashboard: Callable[[], dict]) -> dict:
    result = run_import_capture()
    payload = load_dashboard()
    payload["import_stats"] = result["stats"]
    payload["import_error"] = result["error"]
    payload["import_status"] = result["status"]
    state = payload.get("state")
    if isinstance(state, dict):
        state["import_status"] = result["status"]
    return payload


def auto_import_loop(interval: int, sleep: Callable[[float], None] = time.sleep) -> None:
    while True:
        try:
            run_import()
        except Exception:
            LOGGER.exception("background import iteration failed")
        sleep(interval)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _existing_file(value: str) -> bool:
    return Path(os.path.expandvars(value)).expanduser().is_file()


def _same_path(left: str, right: str) -> bool:
    left_path = Path(os.path.expandvars(left)).expanduser()
    right_path = Path(os.path.expandvars(right)).expanduser()
    return os.path.normcase(str(left_path)) == os.path.normcase(str(right_path))
