from __future__ import annotations

import io
import json
import logging
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.api.handlers import first, parse_limit, parse_ts, read_json_body
from app.api.responses import send_json
from app.core import config as core_config
from app.core.logging_config import configure_logging
from app.services import background
from app.sources.codex.reader import iter_log_rows_after, iter_usage_log_rows, latest_log_id
from app.sources.codex.thread_names import load_thread_names
from app.storage.payloads import compact_event_payload, decode_json
from app.storage.query_params import (
    DEFAULT_BUCKET,
    DEFAULT_RANGE,
    TASK_MODE_AGGREGATE,
    TASK_MODE_SEPARATE,
    normalize_bucket,
    normalize_range,
    normalize_task_mode,
)


class DummyHandler:
    def __init__(self, body: bytes = b"", headers: dict[str, str] | None = None):
        self.headers = headers or {}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status = None
        self.response_headers: list[tuple[str, str]] = []
        self.ended = False

    def send_response(self, status: int):
        self.status = status

    def send_header(self, key: str, value: str):
        self.response_headers.append((key, value))

    def end_headers(self):
        self.ended = True


class ApiHelperTests(unittest.TestCase):
    def test_query_helpers_normalize_values(self):
        query = {"name": ["model-a"], "limit": ["999"], "start_ts": ["123"], "bad_ts": ["nope"]}

        self.assertEqual(first(query, "name"), "model-a")
        self.assertEqual(first(query, "missing", "fallback"), "fallback")
        self.assertEqual(parse_limit(query, default=25, maximum=100), 100)
        self.assertEqual(parse_ts(query, "start_ts"), 123)
        self.assertIsNone(parse_ts(query, "bad_ts"))
        self.assertIsNone(parse_ts(query, "missing"))

    def test_read_json_body_accepts_only_bounded_json_objects(self):
        body = json.dumps({"ok": True}).encode("utf-8")
        handler = DummyHandler(body, {"Content-Length": str(len(body))})

        self.assertEqual(read_json_body(handler), {"ok": True})
        self.assertIsNone(read_json_body(DummyHandler(b"[]", {"Content-Length": "2"})))
        self.assertIsNone(read_json_body(DummyHandler(b"{}", {"Content-Length": "bad"})))
        self.assertIsNone(read_json_body(DummyHandler(b"{}", {"Content-Length": "2"}), max_bytes=1))
        self.assertIsNone(read_json_body(DummyHandler(b"{", {"Content-Length": "1"})))

    def test_send_json_sets_utf8_headers_and_body(self):
        handler = DummyHandler()

        send_json(handler, {"message": "привет"})

        headers = dict(handler.response_headers)
        self.assertEqual(handler.status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(int(headers["Content-Length"]), len(handler.wfile.getvalue()))
        self.assertEqual(json.loads(handler.wfile.getvalue().decode("utf-8")), {"message": "привет"})


class ConfigAndPayloadTests(unittest.TestCase):
    def test_load_config_merges_local_and_resolves_configured_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.json"
            local_path = root / "config.local.json"
            config_path.write_text(
                json.dumps({"analytics_db": "data/analytics.sqlite", "keep": "base"}),
                encoding="utf-8",
            )
            local_path.write_text(
                json.dumps({"codex_logs_db": "~/codex.sqlite", "keep": "local"}),
                encoding="utf-8",
            )

            with mock.patch.object(core_config, "ROOT", root), \
                 mock.patch.object(core_config, "CONFIG_PATH", config_path), \
                 mock.patch.object(core_config, "LOCAL_CONFIG_PATH", local_path):
                config = core_config.load_config()

        self.assertEqual(config["keep"], "local")
        self.assertEqual(config["analytics_db"], str(root / "data" / "analytics.sqlite"))
        self.assertTrue(Path(config["codex_logs_db"]).is_absolute())

    def test_configure_logging_writes_rotating_log_file(self):
        original_handlers = logging.getLogger().handlers[:]
        original_level = logging.getLogger().level
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "token-lens.log"
            try:
                configure_logging(
                    {
                        "log_file": str(log_path),
                        "log_level": "INFO",
                        "log_max_bytes": 10000,
                        "log_backup_count": 1,
                    },
                    force=True,
                )
                logging.getLogger("token_lens.test").info("hello logging")
                for handler in logging.getLogger().handlers:
                    handler.flush()
                content = log_path.read_text(encoding="utf-8")
            finally:
                for handler in logging.getLogger().handlers:
                    handler.close()

        logging.basicConfig(level=original_level, handlers=original_handlers, force=True)
        self.assertIn("hello logging", content)

    def test_payload_helpers_decode_and_compact_response_events(self):
        self.assertEqual(decode_json('{"a":1}'), {"a": 1})
        self.assertEqual(decode_json("{bad"), "{bad")
        self.assertIsNone(decode_json(""))

        event = {
            "type": "response.completed",
            "response": {
                "id": "resp-1",
                "status": "completed",
                "usage": {"total_tokens": 10},
                "instructions": "large",
                "tools": [{"name": "tool"}],
            },
        }

        compacted = compact_event_payload(event)

        self.assertTrue(compacted["compacted"])
        self.assertEqual(compacted["response"]["id"], "resp-1")
        self.assertNotIn("instructions", compacted["response"])
        self.assertEqual(compacted["omitted_response_fields"], ["instructions", "tools"])
        self.assertEqual(compact_event_payload("raw"), "raw")


class QueryParamTests(unittest.TestCase):
    def test_ranges_buckets_and_task_modes_are_normalized(self):
        self.assertEqual(normalize_range("24h"), "24h")
        self.assertEqual(normalize_range("bogus"), DEFAULT_RANGE)
        self.assertEqual(normalize_bucket("hour", "24h"), "hour")
        self.assertEqual(normalize_bucket("month", "24h"), DEFAULT_BUCKET)
        self.assertEqual(normalize_bucket("bogus", "custom"), DEFAULT_BUCKET)
        self.assertEqual(normalize_task_mode(TASK_MODE_SEPARATE, "24h"), TASK_MODE_SEPARATE)
        self.assertEqual(normalize_task_mode(TASK_MODE_SEPARATE, "7d"), TASK_MODE_AGGREGATE)


class CodexSourceHelperTests(unittest.TestCase):
    def test_thread_names_loads_valid_jsonl_rows_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sessions.jsonl"
            path.write_text(
                "\n".join([
                    json.dumps({"id": "thread-1", "thread_name": "First"}),
                    "{bad json",
                    json.dumps({"id": "thread-2"}),
                    json.dumps({"id": "thread-3", "thread_name": "Third"}),
                ]),
                encoding="utf-8",
            )

            names = load_thread_names(str(path))

        self.assertEqual(names, {"thread-1": "First", "thread-3": "Third"})
        self.assertEqual(load_thread_names("missing-file.jsonl"), {})

    def test_codex_reader_filters_usage_and_response_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "logs.sqlite"
            con = sqlite3.connect(db_path)
            try:
                con.execute("create table logs (id integer primary key, ts integer, thread_id text, feedback_log_body text)")
                con.executemany(
                    "insert into logs (id, ts, thread_id, feedback_log_body) values (?, ?, ?, ?)",
                    [
                        (1, 100, "thread-1", "noise"),
                        (2, 101, "thread-1", 'instrument_name="codex.turn.token_usage" codex.turn.token_usage.total_tokens=1'),
                        (3, 102, "thread-2", '{"type":"response.completed","response":{"id":"resp-1"}}'),
                    ],
                )
                con.commit()
            finally:
                con.close()

            usage_rows = list(iter_usage_log_rows(str(db_path)))
            after_rows = list(iter_log_rows_after(str(db_path), 1))
            latest = latest_log_id(str(db_path))

        self.assertEqual([row["id"] for row in usage_rows], [2, 3])
        self.assertEqual([row["id"] for row in after_rows], [2, 3])
        self.assertEqual(latest, 3)


class BackgroundImportTests(unittest.TestCase):
    def test_run_import_records_success_and_failure_state(self):
        class Stats:
            def __init__(self, imported: int):
                self.scanned = imported
                self.imported = imported
                self.skipped = 0
                self.archived = 0

        with (
            mock.patch.object(background, "import_codex_logs", return_value=Stats(2)),
            mock.patch.object(background, "LOGGER"),
        ):
            stats = background.run_import()
            state = background.import_status()

        self.assertEqual(stats.imported, 2)
        self.assertEqual(state["status"], "succeeded")
        self.assertEqual(state["stats"], {"scanned": 2, "imported": 2, "skipped": 0, "archived": 0})
        self.assertIsNone(state["error"])

        with (
            mock.patch.object(background, "import_codex_logs", side_effect=RuntimeError("boom")),
            mock.patch.object(background, "LOGGER"),
        ):
            with self.assertRaises(RuntimeError):
                background.run_import()
            failed = background.import_status()

        self.assertEqual(failed["status"], "failed")
        self.assertIn("RuntimeError: boom", failed["error"])


if __name__ == "__main__":
    unittest.main()
