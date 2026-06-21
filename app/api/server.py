from __future__ import annotations

import threading
import time
from http.server import ThreadingHTTPServer
import logging

from app.api.handlers import AnalyticsHandler
from app.core.config import load_config
from app.core.logging_config import configure_logging
from app.services.background import auto_import_loop, run_import
from app.storage.schema import init_db


LOGGER = logging.getLogger("token_lens.server")


def _run_initial_import_once() -> None:
    try:
        run_import()
    except Exception:
        LOGGER.exception("initial import failed")


def _delayed_auto_import_loop(interval: int) -> None:
    time.sleep(2)
    auto_import_loop(interval)


def _delayed_initial_import_once() -> None:
    time.sleep(2)
    _run_initial_import_once()


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

    if interval > 0:
        thread = threading.Thread(target=_delayed_auto_import_loop, args=(interval,), daemon=True)
        thread.start()
    else:
        thread = threading.Thread(target=_delayed_initial_import_once, daemon=True)
        thread.start()

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
