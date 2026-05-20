from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

from app.api.handlers import AnalyticsHandler
from app.core.config import load_config
from app.services.background import auto_import_loop, run_import
from app.storage.schema import init_db


def main():
    config = load_config()
    init_db(config["analytics_db"])
    run_import()

    interval = int(config.get("auto_import_seconds", 30))
    if interval > 0:
        thread = threading.Thread(target=auto_import_loop, args=(interval,), daemon=True)
        thread.start()

    httpd = ThreadingHTTPServer((config["host"], int(config["port"])), AnalyticsHandler)
    print(f"Token Lens: http://{config['host']}:{config['port']}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
