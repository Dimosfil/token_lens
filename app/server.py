from __future__ import annotations

import json
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import ROOT, load_config
from .db import connect, init_db
from .importer import import_codex_logs


STATIC_DIR = ROOT / "web"
IMPORT_LOCK = threading.Lock()


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def run_import():
    with IMPORT_LOCK:
        return import_codex_logs()


class AnalyticsHandler(BaseHTTPRequestHandler):
    server_version = "TokenLens/0.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api(parsed.path, parse_qs(parsed.query))
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/import":
            stats = run_import()
            self.send_json(stats.__dict__)
            return
        if parsed.path == "/api/refresh":
            stats = run_import()
            config = load_config()
            init_db(config["analytics_db"])
            with connect(config["analytics_db"]) as con:
                payload = self.dashboard(con, parse_qs(parsed.query))
            payload["import_stats"] = stats.__dict__
            self.send_json(payload)
            return
        self.send_error(404)

    def handle_api(self, path: str, query: dict):
        config = load_config()
        init_db(config["analytics_db"])
        with connect(config["analytics_db"]) as con:
            if path == "/api/summary":
                self.send_json(self.summary(con))
            elif path == "/api/state":
                self.send_json(self.data_state(con))
            elif path == "/api/daily":
                self.send_json(self.daily(con))
            elif path == "/api/turns":
                limit = min(int(query.get("limit", ["100"])[0]), 500)
                model = query.get("model", [""])[0]
                self.send_json(self.turns(con, limit, model))
            elif path == "/api/tasks":
                limit = min(int(query.get("limit", ["100"])[0]), 500)
                self.send_json(self.tasks(con, limit))
            elif path == "/api/models":
                self.send_json(self.models(con))
            else:
                self.send_error(404)

    def dashboard(self, con, query: dict):
        model = query.get("model", [""])[0]
        return {
            "state": self.data_state(con),
            "summary": self.summary(con),
            "daily": self.daily(con),
            "turns": self.turns(con, 150, model),
            "tasks": self.tasks(con, 150),
            "models": self.models(con),
        }

    def summary(self, con):
        row = con.execute(
            """
            select count(*) as turns,
                   count(distinct thread_id) as threads,
                   coalesce(sum(input_tokens), 0) as input_tokens,
                   coalesce(sum(output_tokens), 0) as output_tokens,
                   coalesce(sum(cached_input_tokens), 0) as cached_input_tokens,
                   coalesce(sum(reasoning_output_tokens), 0) as reasoning_output_tokens,
                   coalesce(sum(total_tokens), 0) as total_tokens,
                   coalesce(sum(estimated_cost), 0) as estimated_cost,
                   max(ts_iso) as latest_turn
            from turns
            """
        ).fetchone()
        top = con.execute(
            """
            select ts_iso, thread_id, thread_name, turn_id, response_id, status, model, total_tokens,
                   input_tokens, output_tokens, reasoning_output_tokens
            from turns
            order by total_tokens desc
            limit 10
            """
        ).fetchall()
        return {"summary": dict(row), "top_turns": rows_to_dicts(top)}

    def daily(self, con):
        return rows_to_dicts(con.execute(
            """
            select day,
                   count(*) as turns,
                   sum(input_tokens) as input_tokens,
                   sum(output_tokens) as output_tokens,
                   sum(cached_input_tokens) as cached_input_tokens,
                   sum(reasoning_output_tokens) as reasoning_output_tokens,
                   sum(total_tokens) as total_tokens,
                   sum(estimated_cost) as estimated_cost
            from turns
            group by day
            order by day
            """
        ).fetchall())

    def turns(self, con, limit: int, model: str = ""):
        params = []
        where = ""
        if model:
            where = "where model = ?"
            params.append(model)
        params.append(limit)
        return rows_to_dicts(con.execute(
            f"""
            select ts_iso, day, thread_id, thread_name, turn_id, response_id, status, model,
                   reasoning_effort, input_tokens, cached_input_tokens,
                   non_cached_input_tokens, output_tokens,
                   reasoning_output_tokens, total_tokens, estimated_cost
            from turns
            {where}
            order by ts desc
            limit ?
            """,
            params,
        ).fetchall())

    def tasks(self, con, limit: int):
        return rows_to_dicts(con.execute(
            """
            select min(ts_iso) as started_at,
                   max(ts_iso) as finished_at,
                   thread_id,
                   max(thread_name) as thread_name,
                   turn_id,
                   group_concat(distinct model) as models,
                   group_concat(distinct status) as statuses,
                   count(*) as model_calls,
                   sum(input_tokens) as input_tokens,
                   sum(cached_input_tokens) as cached_input_tokens,
                   sum(non_cached_input_tokens) as non_cached_input_tokens,
                   sum(output_tokens) as output_tokens,
                   sum(reasoning_output_tokens) as reasoning_output_tokens,
                   sum(total_tokens) as total_tokens,
                   sum(estimated_cost) as estimated_cost
            from turns
            group by thread_id, turn_id
            order by max(ts) desc
            limit ?
            """,
            (limit,),
        ).fetchall())

    def models(self, con):
        return rows_to_dicts(con.execute(
            """
            select model, count(*) as turns, sum(total_tokens) as total_tokens
            from turns
            group by model
            order by total_tokens desc
            """
        ).fetchall())

    def data_state(self, con):
        row = con.execute(
            """
            select count(*) as turns,
                   coalesce(max(source_log_id), 0) as latest_source_log_id,
                   coalesce(max(ts), 0) as latest_ts,
                   coalesce(sum(total_tokens), 0) as total_tokens
            from turns
            """
        ).fetchone()
        state = dict(row)
        state["version"] = ":".join(str(state[key]) for key in (
            "turns",
            "latest_source_log_id",
            "latest_ts",
            "total_tokens",
        ))
        return state

    def serve_static(self, path: str):
        if path in ("", "/"):
            path = "/index.html"
        candidate = (STATIC_DIR / path.lstrip("/")).resolve()
        if not str(candidate).startswith(str(STATIC_DIR.resolve())) or not candidate.exists():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        data = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        return


def auto_import_loop(interval: int):
    while True:
        try:
            run_import()
        except Exception:
            pass
        time.sleep(interval)


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
