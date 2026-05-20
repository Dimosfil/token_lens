from __future__ import annotations

import threading
import time

from app.services.import_service import import_codex_logs


IMPORT_LOCK = threading.Lock()


def run_import():
    with IMPORT_LOCK:
        return import_codex_logs()


def auto_import_loop(interval: int):
    while True:
        try:
            run_import()
        except Exception:
            pass
        time.sleep(interval)
