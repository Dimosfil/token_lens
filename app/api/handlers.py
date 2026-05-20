from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from app.api.responses import send_json
from app.services import analytics_service
from app.services.background import run_import
from app.static_server import serve_static
from app.storage import queries


class AnalyticsHandler(BaseHTTPRequestHandler):
    server_version = "TokenLens/0.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api(parsed.path, parse_qs(parsed.query))
            return
        serve_static(self, parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/api/import":
            stats = run_import()
            send_json(self, stats.__dict__)
            return
        if parsed.path == "/api/refresh":
            stats = run_import()
            payload = analytics_service.dashboard(query.get("model", [""])[0])
            payload["import_stats"] = stats.__dict__
            send_json(self, payload)
            return
        self.send_error(404)

    def handle_api(self, path: str, query: dict):
        if path == "/api/summary":
            send_json(self, analytics_service.summary())
        elif path == "/api/state":
            send_json(self, analytics_service.data_state())
        elif path == "/api/daily":
            send_json(self, analytics_service.daily())
        elif path == "/api/turns":
            limit = min(int(query.get("limit", ["100"])[0]), 500)
            model = query.get("model", [""])[0]
            send_json(self, analytics_service.turns(limit, model))
        elif path == "/api/tasks":
            limit = min(int(query.get("limit", ["100"])[0]), 500)
            send_json(self, analytics_service.tasks(limit))
        elif path == "/api/models":
            send_json(self, analytics_service.models())
        else:
            self.send_error(404)

    def dashboard(self, con, query: dict):
        return queries.dashboard(con, query.get("model", [""])[0])

    def summary(self, con):
        return queries.summary(con)

    def daily(self, con):
        return queries.daily(con)

    def turns(self, con, limit: int, model: str = ""):
        return queries.turns(con, limit, model)

    def tasks(self, con, limit: int):
        return queries.tasks(con, limit)

    def models(self, con):
        return queries.models(con)

    def data_state(self, con):
        return queries.data_state(con)

    def log_message(self, format, *args):
        return
