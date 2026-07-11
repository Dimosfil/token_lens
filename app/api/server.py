from __future__ import annotations

import threading
import time
from http.server import ThreadingHTTPServer
import logging

from app.api.handlers import AnalyticsHandler
from app.core.config import load_config
from app.core.logging_config import configure_logging
from app.services.data_refresh import auto_import_loop, run_import
from app.storage.schema import init_db


LOGGER = logging.getLogger("token_lens.server")


def _run_initial_import_once() -> None:
    try:
        run_import()
    except Exception:
        LOGGER.exception("initial import failed")


def _delayed_auto_import_loop(
    interval: int,
    sleep=time.sleep,
    loop=auto_import_loop,
) -> None:
    sleep(interval)
    loop(interval)


def _delayed_initial_import_once() -> None:
    time.sleep(2)
    _run_initial_import_once()


def start_import_thread(interval: int) -> threading.Thread | None:
    if interval > 0:
        thread = threading.Thread(target=_delayed_auto_import_loop, args=(interval,), daemon=True)
        thread.start()
        return thread
    if interval == 0:
        thread = threading.Thread(target=_delayed_initial_import_once, daemon=True)
        thread.start()
        return thread
    LOGGER.info("automatic imports disabled auto_import_seconds=%s", interval)
    return None


def main():
    config = load_config()
    log_path = configure_logging(config)
    init_db(config["analytics_db"])

    interval = int(config.get("auto_import_seconds", 30))
    httpd = ThreadingHTTPServer((config["host"], int(config["port"])), AnalyticsHandler)
    LOGGER.info(
        "server starting host=%s port=%s analytics_db=%s auto_import_seconds=%s log_file=%s",
        config["host"],
        config["port"],
        config["analytics_db"],
        interval,
        log_path,
    )

    start_import_thread(interval)

    print(f"Token Lens: http://{config['host']}:{config['port']}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("server interrupted")
    except Exception:
        LOGGER.exception("server crashed")
        raise
    finally:
        LOGGER.info("server stopping")
        httpd.server_close()


if __name__ == "__main__":
    main()
