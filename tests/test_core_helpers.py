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
from app.core.codex_discovery import discover_codex_command, discover_codex_paths, discover_opencode_paths
from app.core.logging_config import configure_logging
from app.core.types import ImportStats
from app.services import background
from app.services import data_refresh
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

    def test_load_config_auto_discovers_codex_paths_when_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            codex_root = home / ".codex"
            logs_db = codex_root / "sqlite" / "logs_2.sqlite"
            sessions = codex_root / "sessions"
            command = codex_root / "bin" / "codex.cmd"
            logs_db.parent.mkdir(parents=True)
            sessions.mkdir()
            command.parent.mkdir(parents=True)
            logs_db.write_text("", encoding="utf-8")
            command.write_text("@echo off\n", encoding="utf-8")
            config_path = root / "config.json"
            local_path = root / "config.local.json"
            config_path.write_text(
                json.dumps({
                    "analytics_db": "data/analytics.sqlite",
                    "codex_logs_db": "",
                    "codex_session_index": "",
                    "auto_discover_codex_sources": True,
                }),
                encoding="utf-8",
            )

            with mock.patch.object(core_config, "ROOT", root), \
                 mock.patch.object(core_config, "CONFIG_PATH", config_path), \
                 mock.patch.object(core_config, "LOCAL_CONFIG_PATH", local_path), \
                 mock.patch.dict(core_config.os.environ, {"USERPROFILE": str(home)}, clear=True):
                config = core_config.load_config()
                local_config = json.loads(local_path.read_text(encoding="utf-8"))

        self.assertEqual(config["codex_logs_db"], str(logs_db))
        self.assertEqual(config["codex_session_index"], str(sessions))
        self.assertEqual(config["codex_app_server_command"], str(command))
        self.assertEqual(local_config["codex_logs_db"], str(logs_db))
        self.assertEqual(local_config["codex_session_index"], str(sessions))
        self.assertEqual(local_config["codex_app_server_command"], str(command))

    def test_load_config_auto_discovers_opencode_paths_when_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            db_path = home / ".local" / "share" / "opencode" / "opencode.db"
            tokens_path = home / ".config" / "opencode" / "logs" / "token-tracker" / "tokens.jsonl"
            db_path.parent.mkdir(parents=True)
            tokens_path.parent.mkdir(parents=True)
            db_path.write_text("", encoding="utf-8")
            tokens_path.write_text("", encoding="utf-8")
            config_path = root / "config.json"
            local_path = root / "config.local.json"
            config_path.write_text(
                json.dumps({
                    "analytics_db": "data/analytics.sqlite",
                    "opencode_db": "",
                    "opencode_tokens_jsonl": "",
                }),
                encoding="utf-8",
            )

            with mock.patch.object(core_config, "ROOT", root), \
                 mock.patch.object(core_config, "CONFIG_PATH", config_path), \
                 mock.patch.object(core_config, "LOCAL_CONFIG_PATH", local_path), \
                 mock.patch.dict(core_config.os.environ, {"USERPROFILE": str(home)}, clear=True):
                config = core_config.load_config()
                local_config = json.loads(local_path.read_text(encoding="utf-8"))

        self.assertEqual(config["opencode_db"], str(db_path))
        self.assertEqual(config["opencode_tokens_jsonl"], str(tokens_path))
        self.assertEqual(local_config["opencode_db"], str(db_path))
        self.assertEqual(local_config["opencode_tokens_jsonl"], str(tokens_path))

    def test_load_config_keeps_explicit_local_codex_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            explicit = root / "explicit.sqlite"
            explicit.write_text("", encoding="utf-8")
            home = root / "home"
            discovered = home / ".codex" / "sqlite" / "logs_2.sqlite"
            discovered.parent.mkdir(parents=True)
            discovered.write_text("", encoding="utf-8")
            config_path = root / "config.json"
            local_path = root / "config.local.json"
            config_path.write_text(json.dumps({"analytics_db": "data/analytics.sqlite"}), encoding="utf-8")
            local_path.write_text(json.dumps({"codex_logs_db": str(explicit)}), encoding="utf-8")

            with mock.patch.object(core_config, "ROOT", root), \
                 mock.patch.object(core_config, "CONFIG_PATH", config_path), \
                 mock.patch.object(core_config, "LOCAL_CONFIG_PATH", local_path), \
                 mock.patch.dict(core_config.os.environ, {"USERPROFILE": str(home)}, clear=True):
                config = core_config.load_config()

        self.assertEqual(config["codex_logs_db"], str(explicit))

    def test_discover_codex_paths_prefers_current_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            logs_db = home / ".codex" / "sqlite" / "logs_2.sqlite"
            legacy_logs = home / ".codex" / "logs_2.sqlite"
            sessions = home / ".codex" / "sessions"
            logs_db.parent.mkdir(parents=True)
            sessions.mkdir()
            logs_db.write_text("", encoding="utf-8")
            legacy_logs.write_text("", encoding="utf-8")

            discovered = discover_codex_paths({"USERPROFILE": str(home)})

        self.assertEqual(discovered["codex_logs_db"], str(logs_db))
        self.assertEqual(discovered["codex_session_index"], str(sessions))

    def test_discover_codex_paths_uses_newer_legacy_logs_when_current_layout_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            logs_db = home / ".codex" / "sqlite" / "logs_2.sqlite"
            legacy_logs = home / ".codex" / "logs_2.sqlite"
            logs_db.parent.mkdir(parents=True)
            logs_db.write_text("", encoding="utf-8")
            legacy_logs.write_text("", encoding="utf-8")
            old_time = 1_700_000_000
            new_time = old_time + 60
            core_config.os.utime(logs_db, (old_time, old_time))
            core_config.os.utime(legacy_logs, (new_time, new_time))

            discovered = discover_codex_paths({"USERPROFILE": str(home)})

        self.assertEqual(discovered["codex_logs_db"], str(legacy_logs))

    def test_discover_opencode_paths_checks_standard_user_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            db_path = home / ".local" / "share" / "opencode" / "opencode.db"
            tokens_path = home / ".config" / "opencode" / "logs" / "token-tracker" / "tokens.jsonl"
            db_path.parent.mkdir(parents=True)
            tokens_path.parent.mkdir(parents=True)
            db_path.write_text("", encoding="utf-8")
            tokens_path.write_text("", encoding="utf-8")

            discovered = discover_opencode_paths({"USERPROFILE": str(home)})

        self.assertEqual(discovered["opencode_db"], str(db_path))
        self.assertEqual(discovered["opencode_tokens_jsonl"], str(tokens_path))

    def test_discover_codex_command_checks_codex_bin(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            command = home / ".codex" / "bin" / "codex.cmd"
            command.parent.mkdir(parents=True)
            command.write_text("@echo off\n", encoding="utf-8")

            discovered = discover_codex_command({"USERPROFILE": str(home)})

        self.assertEqual(discovered, str(command))

    def test_discover_codex_command_ignores_windowsapps_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            alias = Path(tmp) / "WindowsApps" / "codex.exe"
            alias.parent.mkdir(parents=True)
            alias.write_text("", encoding="utf-8")

            with mock.patch("app.core.codex_discovery.shutil.which", return_value=str(alias)):
                discovered = discover_codex_command({"USERPROFILE": str(Path(tmp) / "home")})

        self.assertIsNone(discovered)

    def test_codex_source_validation_reports_missing_or_unreadable_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = str(Path(tmp) / "missing.sqlite")
            issues = core_config.validate_codex_source_config({"codex_logs_db": missing_path})

        self.assertTrue(any("codex_logs_db does not exist" in issue for issue in issues))

        issues = core_config.validate_codex_source_config({"codex_logs_db": ""})
        self.assertIn("codex_logs_db is not configured", issues)

    def test_codex_source_validation_accepts_session_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs_db = root / "logs.sqlite"
            sessions = root / "sessions"
            logs_db.write_text("", encoding="utf-8")
            sessions.mkdir()

            issues = core_config.validate_codex_source_config({
                "codex_logs_db": str(logs_db),
                "codex_session_index": str(sessions),
            })

        self.assertEqual(issues, [])

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
                    json.dumps({"thread_id": "thread-4", "title": "Fourth"}),
                    json.dumps({"payload": {"id": "thread-5", "title": "Fifth"}}),
                    json.dumps({"payload": {"session_id": "thread-6", "conversation_title": "Sixth"}}),
                ]),
                encoding="utf-8",
            )

            names = load_thread_names(str(path))

        self.assertEqual(names, {
            "thread-1": "First",
            "thread-3": "Third",
            "thread-4": "Fourth",
            "thread-5": "Fifth",
            "thread-6": "Sixth",
        })
        self.assertEqual(load_thread_names("missing-file.jsonl"), {})

    def test_thread_names_loads_directory_and_glob_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            day = root / "sessions" / "2026" / "06" / "24"
            day.mkdir(parents=True)
            (day / "rollout-a.jsonl").write_text(
                json.dumps({"id": "thread-a", "thread_name": "Alpha"}) + "\n",
                encoding="utf-8",
            )
            (day / "rollout-b.jsonl").write_text(
                json.dumps({"id": "thread-b", "thread_name": "Beta"}) + "\n",
                encoding="utf-8",
            )

            directory_names = load_thread_names(str(root / "sessions"))
            glob_names = load_thread_names(str(day / "rollout-*.jsonl"))

        self.assertEqual(directory_names, {"thread-a": "Alpha", "thread-b": "Beta"})
        self.assertEqual(glob_names, {"thread-a": "Alpha", "thread-b": "Beta"})

    def test_thread_names_legacy_index_includes_sibling_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "session_index.jsonl"
            day = root / "sessions" / "2026" / "06" / "25"
            day.mkdir(parents=True)
            legacy.write_text(
                json.dumps({"id": "thread-old", "thread_name": "Old title"}) + "\n",
                encoding="utf-8",
            )
            (day / "rollout-new.jsonl").write_text(
                json.dumps({"payload": {"id": "thread-new", "title": "New title"}}) + "\n",
                encoding="utf-8",
            )

            names = load_thread_names(str(legacy))

        self.assertEqual(names, {"thread-old": "Old title", "thread-new": "New title"})

    def test_thread_names_derives_title_from_session_user_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(
                "\n".join([
                    json.dumps({"type": "session_meta", "payload": {"id": "thread-new"}}),
                    json.dumps({
                        "type": "response_item",
                        "payload": {
                            "role": "user",
                            "content": "# AGENTS.md instructions <INSTRUCTIONS> internal setup",
                        },
                    }),
                    json.dumps({
                        "type": "response_item",
                        "payload": {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": (
                                        "# Files mentioned by the user:\n\n"
                                        "## screenshot.png\n\n"
                                        "## My request for Codex:\n"
                                        "  Restore\nCodex chat labels in mini  "
                                    ),
                                },
                            ],
                        },
                    }),
                ]),
                encoding="utf-8",
            )

            names = load_thread_names(str(path))

        self.assertEqual(names, {"thread-new": "Restore Codex chat labels in mini"})

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
                        (4, 103, "thread-3", "turn.id=turn-3 model=gpt-5 codex.turn.token_usage.total_tokens=2"),
                        (5, 104, "thread-4", "event.name=\"codex.sse_event\" event.kind=response.completed"),
                    ],
                )
                con.commit()
            finally:
                con.close()

            usage_rows = list(iter_usage_log_rows(str(db_path)))
            after_rows = list(iter_log_rows_after(str(db_path), 1))
            latest = latest_log_id(str(db_path))

        self.assertEqual([row["id"] for row in usage_rows], [2, 3, 4, 5])
        self.assertEqual([row["id"] for row in after_rows], [2, 3, 4, 5])
        self.assertEqual(latest, 5)


class BackgroundImportTests(unittest.TestCase):
    def test_import_status_returns_current_state(self):
        with (
            mock.patch.object(data_refresh, "source_warnings", return_value=[]),
            mock.patch.object(data_refresh, "import_codex_logs", return_value=ImportStats(scanned=2, imported=2)),
            mock.patch.object(data_refresh, "import_opencode_sources", return_value=ImportStats()),
            mock.patch.object(data_refresh, "LOGGER"),
        ):
            data_refresh.run_import()
            state = data_refresh.import_status()

        self.assertEqual(state["status"], "succeeded")
        self.assertEqual(state["stats"], {"scanned": 2, "imported": 2, "skipped": 0, "archived": 0})
        self.assertIsNone(state["error"])

    def test_source_warnings_reports_legacy_readable_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            configured = Path(tmp) / "logs_2.sqlite"
            preferred = Path(tmp) / "sqlite" / "logs_2.sqlite"
            preferred.parent.mkdir()
            configured.write_text("", encoding="utf-8")
            preferred.write_text("", encoding="utf-8")

            warnings = data_refresh.source_warnings(
                {"codex_logs_db": str(configured)},
                {"codex_logs_db": str(preferred)},
            )
            clean = data_refresh.source_warnings(
                {"codex_logs_db": str(preferred)},
                {"codex_logs_db": str(preferred)},
            )

        self.assertEqual(len(warnings), 1)
        self.assertIn("preferred discovered Codex SQLite source", warnings[0])
        self.assertEqual(clean, [])

    def test_run_import_records_success_and_failure_state(self):
        with (
            mock.patch.object(data_refresh, "source_warnings", return_value=["warn"]),
            mock.patch.object(data_refresh, "import_codex_logs", return_value=ImportStats(scanned=2, imported=2)),
            mock.patch.object(data_refresh, "import_opencode_sources", return_value=ImportStats()),
            mock.patch.object(data_refresh, "LOGGER"),
        ):
            stats = data_refresh.run_import()
            state = data_refresh.import_status()

        self.assertEqual(stats.imported, 2)
        self.assertEqual(state["status"], "succeeded")
        self.assertEqual(state["warnings"], ["warn"])

        with (
            mock.patch.object(data_refresh, "source_warnings", return_value=[]),
            mock.patch.object(data_refresh, "import_codex_logs", side_effect=RuntimeError("boom")),
            mock.patch.object(data_refresh, "import_opencode_sources", return_value=ImportStats()),
            mock.patch.object(data_refresh, "LOGGER"),
        ):
            with self.assertRaises(RuntimeError):
                data_refresh.run_import()
            failed = data_refresh.import_status()

        self.assertEqual(failed["status"], "failed")
        self.assertIn("RuntimeError: boom", failed["error"])

    def test_run_import_capture_returns_payload_instead_of_raising(self):
        with mock.patch.object(data_refresh, "run_import", return_value=ImportStats(imported=3)):
            success = data_refresh.run_import_capture()

        self.assertEqual(success["stats"]["imported"], 3)
        self.assertIsNone(success["error"])
        self.assertIn("status", success)

        with mock.patch.object(data_refresh, "run_import", side_effect=RuntimeError("bad import")):
            failure = data_refresh.run_import_capture()

        self.assertIsNone(failure["stats"])
        self.assertEqual(failure["error"], "bad import")
        self.assertIn("status", failure)

    def test_refresh_dashboard_adds_import_result_to_payload(self):
        import_status = {"status": "succeeded", "stats": {"imported": 1}}
        with mock.patch.object(
            data_refresh,
            "run_import_capture",
            return_value={"stats": {"imported": 1}, "error": None, "status": import_status},
        ):
            payload = data_refresh.refresh_dashboard(lambda: {"state": {"version": "v1"}, "tasks": []})

        self.assertEqual(payload["import_stats"], {"imported": 1})
        self.assertIsNone(payload["import_error"])
        self.assertEqual(payload["import_status"], import_status)
        self.assertEqual(payload["state"]["import_status"], import_status)

    def test_auto_import_loop_runs_until_sleep_stops_it(self):
        calls = []

        def stop_after_first(_interval):
            raise KeyboardInterrupt()

        with (
            mock.patch.object(data_refresh, "run_import", side_effect=lambda: calls.append("run")),
            mock.patch.object(data_refresh, "LOGGER"),
        ):
            with self.assertRaises(KeyboardInterrupt):
                data_refresh.auto_import_loop(30, sleep=stop_after_first)

        self.assertEqual(calls, ["run"])

    def test_background_module_keeps_compatibility_exports(self):
        self.assertIs(background.run_import, data_refresh.run_import)
        self.assertIs(background.import_status, data_refresh.import_status)
        self.assertIs(background.auto_import_loop, data_refresh.auto_import_loop)


if __name__ == "__main__":
    unittest.main()
