from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from app.api.responses import send_json
from app.services import analytics_service
from app.services.background import run_import
from app.services.opencode_ingest import ingest_event
from app.static_server import serve_static
from app.storage import queries


LOGGER = logging.getLogger("token_lens.api")


def first(query: dict, key: str, default: str = "") -> str:
    return query.get(key, [default])[0]


def parse_limit(query: dict, default: int = 100, maximum: int = 500) -> int:
    try:
        limit = int(first(query, "limit", str(default)))
    except ValueError:
        limit = default
    return min(max(limit, 1), maximum)


def parse_ts(query: dict, key: str) -> int | None:
    value = first(query, key)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def read_json_body(handler: BaseHTTPRequestHandler, max_bytes: int = 2_000_000) -> dict | None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        length = 0
    if length <= 0 or length > max_bytes:
        return None
    body = handler.rfile.read(length)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


class AnalyticsHandler(BaseHTTPRequestHandler):
    server_version = "TokenLens/0.1"

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self.handle_api(parsed.path, parse_qs(parsed.query))
                return
            serve_static(self, parsed.path)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            LOGGER.info("client disconnected method=GET path=%s", self.path)
        except Exception:
            LOGGER.exception("request failed method=GET path=%s", self.path)
            raise

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            start_ts = parse_ts(query, "start_ts")
            end_ts = parse_ts(query, "end_ts")
            if parsed.path == "/api/import":
                stats = run_import()
                send_json(self, stats.__dict__)
                return
            if parsed.path == "/api/refresh":
                stats = run_import()
                payload = analytics_service.dashboard(
                    first(query, "model"),
                    first(query, "range"),
                    first(query, "bucket", "day"),
                    first(query, "task_mode"),
                    start_ts,
                    end_ts,
                    first(query, "source"),
                )
                payload["import_stats"] = stats.__dict__
                send_json(self, payload)
                return
            if parsed.path == "/api/ingest/opencode":
                payload = read_json_body(self)
                if payload is None:
                    self.send_error(400, "valid JSON object body is required")
                    return
                send_json(self, ingest_event(payload))
                return
            self.send_error(404)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            LOGGER.info("client disconnected method=POST path=%s", self.path)
        except Exception:
            LOGGER.exception("request failed method=POST path=%s", self.path)
            raise

    def handle_api(self, path: str, query: dict):
        range_key = first(query, "range")
        bucket = first(query, "bucket", "day")
        start_ts = parse_ts(query, "start_ts")
        end_ts = parse_ts(query, "end_ts")
        if path == "/api/dashboard":
            send_json(self, analytics_service.dashboard(
                first(query, "model"),
                range_key,
                bucket,
                first(query, "task_mode"),
                start_ts,
                end_ts,
                first(query, "source"),
            ))
        elif path == "/api/summary":
            send_json(self, analytics_service.summary(range_key, start_ts, end_ts, first(query, "source")))
        elif path == "/api/state":
            send_json(self, analytics_service.data_state())
        elif path == "/api/usage-limits":
            send_json(self, analytics_service.usage_limits())
        elif path == "/api/import-status":
            send_json(self, analytics_service.background_import_status())
        elif path == "/api/daily":
            send_json(self, analytics_service.daily(range_key, bucket, start_ts, end_ts, first(query, "source")))
        elif path == "/api/turns":
            limit = parse_limit(query)
            model = first(query, "model")
            send_json(self, analytics_service.turns(limit, model, range_key, start_ts, end_ts, first(query, "source")))
        elif path == "/api/tasks":
            limit = parse_limit(query)
            send_json(self, analytics_service.tasks(limit, range_key, start_ts, end_ts, first(query, "source")))
        elif path == "/api/bucket-tasks":
            period = first(query, "period")
            if not period:
                self.send_error(400, "period is required")
                return
            send_json(self, analytics_service.bucket_tasks(period, bucket, range_key, start_ts, end_ts, first(query, "source")))
        elif path == "/api/task-detail":
            thread_id = first(query, "thread_id")
            turn_id = first(query, "turn_id")
            if not thread_id or not turn_id:
                self.send_error(400, "thread_id and turn_id are required")
                return
            send_json(self, analytics_service.task_detail(thread_id, turn_id))
        elif path == "/api/models":
            send_json(self, analytics_service.models(range_key, start_ts, end_ts, first(query, "source")))
        else:
            self.send_error(404)

    def dashboard(self, con, query: dict):
        return queries.dashboard(
            con,
            first(query, "model"),
            first(query, "range"),
            first(query, "bucket", "day"),
            first(query, "task_mode"),
            parse_ts(query, "start_ts"),
            parse_ts(query, "end_ts"),
        )

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
        LOGGER.debug(
            "http client=%s request=%s",
            self.address_string(),
            format % args,
        )

    def log_request(self, code="-", size="-"):
        try:
            status_code = int(code)
        except (TypeError, ValueError):
            status_code = 0
        level = logging.INFO if status_code >= 400 else logging.DEBUG
        LOGGER.log(
            level,
            "http client=%s method=%s path=%s status=%s size=%s",
            self.address_string(),
            self.command,
            self.path,
            code,
            size,
        )

    def log_error(self, format, *args):
        LOGGER.warning(
            "http error client=%s request=%s",
            self.address_string(),
            format % args,
        )
