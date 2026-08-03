from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from urllib.error import URLError

from desktop import mini_client


class MiniClientHelperTests(unittest.TestCase):
    def test_numeric_and_setting_helpers_are_bounded(self):
        self.assertEqual(mini_client.clamp(100, 1, 50), 50)
        self.assertEqual(mini_client.format_number("12345"), "12 345")
        self.assertEqual(mini_client.format_number("bad"), "0")
        self.assertEqual(mini_client.format_cost("0.123456"), "$0.1235")
        self.assertEqual(mini_client.format_cost("bad"), "$0.0000")
        self.assertEqual(mini_client.parse_int("bad", 7), 7)
        self.assertEqual(mini_client.setting_int({"limit": "999"}, "limit", 4, 1, 50), 50)
        self.assertFalse(mini_client.setting_bool({"signal": "off"}, "signal", True))
        self.assertTrue(mini_client.setting_bool({"signal": "yes"}, "signal", False))
        self.assertEqual(mini_client.setting_str({"range": 123}, "range", "24h"), "24h")
        self.assertEqual(mini_client.normalize_source("opencode"), "opencode")
        self.assertEqual(mini_client.normalize_source("bad"), "codex")
        self.assertEqual(mini_client.setting_columns({"columns": ["task", "cost"]}), ("task", "cost"))
        self.assertEqual(mini_client.setting_columns({"columns": "date,task,bad,task"}), ("date", "task"))
        self.assertEqual(mini_client.setting_columns({"columns": []}), mini_client.DEFAULT_VISIBLE_COLUMNS)
        settings = {
            "limit": 8,
            "columns": ["date", "task"],
            "agents": {
                "opencode": {
                    "limit": 12,
                    "columns": ["task", "total"],
                    "signal": "Hand",
                },
            },
        }
        self.assertEqual(mini_client.setting_int_for_source(settings, "codex", "limit", 4, 1, 50), 8)
        self.assertEqual(mini_client.setting_int_for_source(settings, "opencode", "limit", 4, 1, 50), 12)
        self.assertEqual(mini_client.setting_columns_for_source(settings, "codex"), ("date", "task"))
        self.assertEqual(mini_client.setting_columns_for_source(settings, "opencode"), ("task", "total"))
        self.assertEqual(mini_client.setting_str_for_source(settings, "opencode", "signal", "Simple"), "Hand")

    def test_task_and_time_formatters_hide_machine_ids_when_possible(self):
        self.assertTrue(mini_client.looks_like_id("thread_abcdefghijkl"))
        self.assertFalse(mini_client.looks_like_id("Human task"))
        self.assertEqual(mini_client.task_name({"thread_name": "Investigate costs"}), "Investigate costs")
        self.assertEqual(mini_client.task_name({"thread_name": "thread_abcdefghijkl", "period": "2026-06-19"}), "2026-06-19")
        self.assertEqual(mini_client.task_name({"thread_id": "019f18d1-dbb8-7921-ae8c-324cc9077520", "turn_id": "chat:019f18d1-dbb8-7921-ae8c-324cc9077520"}), "Chat 077520")
        self.assertEqual(
            mini_client.task_name({
                "thread_id": "019f1938-86f9-7c91-afac-d6006ee07941",
                "turn_id": "chat:019f1938-86f9-7c91-afac-d6006ee07941",
                "models": "gpt-5.4-mini",
            }),
            "Mini call e07941",
        )
        self.assertEqual(
            mini_client.task_name({
                "source": "opencode",
                "thread_name": "One OpenCode chat",
                "started_at": "2026-06-23T14:26:30+00:00",
            }),
            "One OpenCode chat",
        )
        self.assertEqual(mini_client.format_duration(3661), "1:01:01")
        self.assertEqual(mini_client.format_duration("bad"), "0:00")
        expected_time = datetime.fromisoformat("2026-06-19T10:25:30+00:00").astimezone().strftime("%Y-%m-%d %H:%M")
        self.assertEqual(mini_client.format_timestamp("2026-06-19T10:25:30+00:00"), expected_time)
        expected_date = datetime.fromisoformat("2026-06-19T10:25:30+00:00").astimezone().strftime("%Y-%m-%d")
        self.assertEqual(mini_client.format_date("2026-06-19T10:25:30+00:00"), expected_date)
        self.assertEqual(mini_client.row_date({"day": "2026-06-20"}), "2026-06-20")
        self.assertEqual(
            mini_client.row_datetime({"finished_at": "2026-06-19T10:25:30+00:00"}),
            expected_time,
        )
        self.assertEqual(
            mini_client.table_cell_value("date_time", {"finished_at": "2026-06-19T10:25:30+00:00"}),
            expected_time,
        )
        raw_only = {"has_usage": 0, "model_calls": 0, "total_tokens_per_call": None, "total_tokens": None}
        self.assertEqual(mini_client.table_cell_value("time", raw_only), "-")
        self.assertEqual(mini_client.table_cell_value("calls", raw_only), "-")
        self.assertEqual(mini_client.table_cell_value("per_call", raw_only), "-")
        self.assertEqual(mini_client.table_cell_value("total", raw_only), "-")
        self.assertEqual(mini_client.table_cell_value("cost", raw_only), "-")

    def test_usage_limit_helpers_group_and_format_windows(self):
        snapshot = {
            "ok": True,
            "stale": True,
            "fetched_at": "2026-07-01T14:45:12+00:00",
            "windows": [
                {"limit_id": "spark", "display_name": "GPT-5.3-Codex-Spark", "label": "weekly", "remaining_percent": 100},
                {"limit_id": "codex", "display_name": "Codex", "label": "5h", "remaining_percent": 25},
            ],
        }

        groups = mini_client.usage_limit_groups(snapshot)
        text = mini_client.usage_limits_text(snapshot)

        self.assertEqual([mini_client.usage_limit_name(group) for group in groups], ["Codex", "Spark"])
        self.assertEqual(mini_client.limit_period({"label": "weekly"}), "week")
        self.assertEqual(mini_client.limit_remaining_percent({"remaining_percent": "150"}), 100)
        self.assertIn("Codex 5h: 25% left", text)
        self.assertIn("Spark week: 100% left", text)
        self.assertTrue(mini_client.usage_limits_updated_text(snapshot).startswith("last updated "))
        stale = mini_client.stale_usage_limits_snapshot(snapshot, "timed out")
        self.assertTrue(stale["ok"])
        self.assertTrue(stale["stale"])
        self.assertEqual(stale["stale_error"], "timed out")
        self.assertEqual(mini_client.usage_limits_text({"ok": False, "error": "offline"}), "Limits: offline")

    def test_import_status_error_text_is_compact(self):
        self.assertEqual(mini_client.import_status_error_text(None), "")
        self.assertEqual(mini_client.import_status_error_text({"status": "succeeded"}), "")
        self.assertEqual(mini_client.backend_status_text("online", "Checked 10:00"), "Backend online · Checked 10:00")
        self.assertEqual(mini_client.backend_status_text("busy", "Importing data"), "Backend busy · Importing data")
        self.assertEqual(mini_client.backend_status_text("offline", "Error: refused"), "Backend offline · Error: refused")
        self.assertEqual(
            mini_client.import_status_error_text({"status": "failed", "error": "codex: locked"}),
            "Import error: codex: locked",
        )
        self.assertEqual(
            mini_client.refresh_status_text({"status": "succeeded"}, ["legacy source"]),
            "Import warning: legacy source",
        )
        self.assertEqual(
            mini_client.refresh_status_text({"status": "failed", "error": "codex: locked"}, ["legacy source"]),
            "Import error: codex: locked",
        )

    def test_limit_bar_fill_color_highlights_full_and_low_remaining(self):
        self.assertEqual(mini_client.limit_bar_fill_color(100), "#1d8f45")
        self.assertEqual(mini_client.limit_bar_fill_color(64), "#0f7c80")
        self.assertEqual(mini_client.limit_bar_fill_color(25), "#c87900")
        self.assertEqual(mini_client.limit_bar_fill_color(5), "#b3261e")

    def test_signal_fires_when_seen_row_crosses_threshold(self):
        class Var:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.current_limit = lambda: 4
        app.active_vars = lambda: {
            "signal_enabled": Var(True),
            "signal_name": Var("Exclamation"),
        }
        app.seen_signal_rows = set()
        app.signal_row_values = {}
        app.signal_seen_initialized = False
        app.last_signal_key = None
        app.last_signal_threshold = None
        app.play_signal = mock.Mock()
        row = {
            "thread_id": "thread-1",
            "turn_id": "turn-1",
            "has_usage": 1,
            "total_tokens_per_call": 90000,
        }

        app.maybe_signal([row], version=1, threshold=100000)
        app.play_signal.assert_not_called()

        row["total_tokens_per_call"] = 120000
        app.maybe_signal([row], version=2, threshold=100000)

        app.play_signal.assert_called_once()

    def test_mini_settings_round_trip_uses_configured_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                mini_client.save_mini_settings({"limit": 5, "range": "24h"})
                loaded = mini_client.load_mini_settings()
                loaded_with_status = mini_client.load_mini_settings_with_status()

        self.assertEqual(loaded, {"limit": 5, "range": "24h"})
        self.assertEqual(loaded_with_status, ({"limit": 5, "range": "24h"}, True))

    def test_mini_settings_writes_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                mini_client.save_mini_settings({"limit": 7})
                backup = mini_client._mini_settings_backup_path()
                backup_exists = backup.exists()
                backup_text = backup.read_text(encoding="utf-8").strip()

        self.assertTrue(backup_exists)
        self.assertEqual(backup_text, '{\n  "limit": 7\n}')

    def test_missing_mini_settings_allows_first_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                loaded, save_enabled = mini_client.load_mini_settings_with_status()

        self.assertEqual(loaded, {})
        self.assertTrue(save_enabled)

    def test_invalid_mini_settings_recovers_from_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            settings_path.write_text("{broken", encoding="utf-8")
            settings_path.with_name("mini_settings.json.bak").write_text('{"limit": 9}', encoding="utf-8")
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                loaded, save_enabled = mini_client.load_mini_settings_with_status()
                repaired = mini_client.json.loads(settings_path.read_text(encoding="utf-8"))

        self.assertEqual(loaded, {"limit": 9})
        self.assertTrue(save_enabled)
        self.assertEqual(repaired, {"limit": 9})

    def test_invalid_mini_settings_without_backup_allows_new_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            settings_path.write_text("{broken", encoding="utf-8")
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                loaded, save_enabled = mini_client.load_mini_settings_with_status()
                corrupt_files = list(Path(tmp).glob("mini_settings.json.corrupt-*"))

        self.assertEqual(loaded, {})
        self.assertTrue(save_enabled)
        self.assertEqual(len(corrupt_files), 1)

    def test_local_api_and_refused_connection_detection(self):
        self.assertTrue(mini_client.is_local_api_url("http://127.0.0.1:8765"))
        self.assertTrue(mini_client.is_local_api_url("http://localhost:8765"))
        self.assertFalse(mini_client.is_local_api_url("https://example.com"))
        self.assertTrue(mini_client.is_connection_refused(URLError(ConnectionRefusedError(10061, "refused"))))
        self.assertFalse(mini_client.is_connection_refused(URLError(TimeoutError("slow"))))

    def test_local_api_client_disables_environment_proxies(self):
        local_opener = mock.Mock()
        with mock.patch.object(mini_client, "build_opener", return_value=local_opener) as build:
            client = mini_client.ApiClient("http://127.0.0.1:8765")

        handler = build.call_args.args[0]
        self.assertEqual(handler.proxies, {})
        self.assertIs(client._local_opener, local_opener)

    def test_remote_api_client_preserves_default_proxy_handling(self):
        with mock.patch.object(mini_client, "build_opener") as build:
            client = mini_client.ApiClient("https://example.com")

        build.assert_not_called()
        self.assertIsNone(client._local_opener)

    def test_server_start_reuses_live_recovery_process(self):
        process = mock.Mock(pid=1234)
        process.poll.return_value = None

        with (
            mock.patch.object(mini_client, "_server_process", process),
            mock.patch.object(mini_client.subprocess, "Popen") as popen,
        ):
            result = mini_client.start_local_server_process()

        self.assertIs(result, process)
        popen.assert_not_called()

    def test_mini_client_recovers_local_refused_connection_once(self):
        class Status:
            def __init__(self):
                self.values = []

            def set(self, value):
                self.values.append(value)

        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.api = mini_client.ApiClient("http://127.0.0.1:8765")
        app.last_server_start_attempt = 0.0
        app.status_var = Status()
        app._ui = lambda callback: callback()
        error = URLError(ConnectionRefusedError(10061, "refused"))

        with (
            mock.patch.object(mini_client, "start_local_server_process") as start,
            mock.patch.object(mini_client, "wait_for_api", return_value=True) as wait,
            mock.patch.object(mini_client.time, "monotonic", return_value=100.0),
            mock.patch.object(mini_client, "LOGGER"),
        ):
            recovered = app.try_recover_local_server(error)

        self.assertTrue(recovered)
        start.assert_called_once()
        wait.assert_called_once_with(app.api)
        self.assertEqual(app.status_var.values[-1], "Backend online · Local server restarted")

        with (
            mock.patch.object(mini_client.time, "monotonic", return_value=105.0),
            mock.patch.object(mini_client, "LOGGER"),
        ):
            self.assertFalse(app.try_recover_local_server(error))

    def test_mini_client_does_not_start_server_for_remote_api(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.api = mini_client.ApiClient("https://example.com")
        app.last_server_start_attempt = 0.0

        with mock.patch.object(mini_client, "start_local_server_process") as start:
            recovered = app.try_recover_local_server(URLError(ConnectionRefusedError(10061, "refused")))

        self.assertFalse(recovered)
        start.assert_not_called()

    def test_worker_ui_callbacks_wait_for_main_thread_queue_drain(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.closed = False
        app.ui_after_id = None
        app.ui_queue = mini_client.queue.Queue()
        app.root = mock.Mock()
        calls = []

        app._ui(lambda: calls.append("rendered"))

        self.assertEqual(calls, [])
        app._drain_ui_queue()
        self.assertEqual(calls, ["rendered"])
        app.root.after.assert_called_once_with(mini_client.UI_QUEUE_POLL_MS, app._drain_ui_queue)

    def test_ui_queue_continues_after_callback_failure(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.closed = False
        app.ui_after_id = None
        app.ui_queue = mini_client.queue.Queue()
        app.root = mock.Mock()
        calls = []
        app.ui_queue.put(lambda: 1 / 0)
        app.ui_queue.put(lambda: calls.append("rendered"))

        with mock.patch.object(mini_client.LOGGER, "exception") as log_exception:
            app._drain_ui_queue()

        self.assertEqual(calls, ["rendered"])
        log_exception.assert_called_once_with("mini UI callback failed")
        app.root.after.assert_called_once_with(mini_client.UI_QUEUE_POLL_MS, app._drain_ui_queue)

    def test_worker_error_callback_keeps_exception_after_except_scope(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        error = URLError("offline")
        callbacks = []
        app.run_with_api_recovery = mock.Mock(side_effect=error)
        app.set_error = mock.Mock()
        app._finish_worker = mock.Mock()
        app._ui = callbacks.append

        app._poll_worker({"source": "codex"})

        callbacks[0]()
        callbacks[1]()
        app.set_error.assert_called_once_with(error)
        app._finish_worker.assert_called_once_with()

    def test_request_snapshot_reads_widget_state_before_worker_starts(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.range_key = "24h"
        app.current_source = mock.Mock(return_value="codex")
        app.current_limit = mock.Mock(return_value=20)

        snapshot = app.request_snapshot()

        self.assertEqual(snapshot, {
            "source": "codex",
            "query": {"limit": 20, "range": "24h", "source": "codex"},
            "source_query": {"range": "24h", "source": "codex"},
        })
        app.current_source.assert_called_once_with()
        app.current_limit.assert_called_once_with()

    def test_unchanged_poll_skips_source_context_until_throttle_expires(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.data_version = 7
        app.refresh_ms = 5000
        app.api = mock.Mock()
        app.api.get_json.return_value = {"version": 7, "import_status": {"status": "succeeded"}}
        app.load_source_context = mock.Mock()
        app.load_rows = mock.Mock()
        app.set_checked_status = mock.Mock()
        app.render_source_context = mock.Mock()
        app.render_rows = mock.Mock()
        app._ui = lambda callback: callback()
        app.last_source_context_refresh = {"codex": 100.0}
        request = {"source": "codex", "query": {"limit": 20, "source": "codex"}}

        with mock.patch.object(mini_client.time, "monotonic", return_value=104.0):
            app.poll_once(request)

        app.api.get_json.assert_called_once_with("/api/state", {"include_raw": 0})
        app.load_source_context.assert_not_called()
        app.load_rows.assert_not_called()
        app.render_source_context.assert_not_called()
        app.render_rows.assert_not_called()
        app.set_checked_status.assert_called_once()

    def test_unchanged_poll_refreshes_source_context_after_throttle(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.data_version = 7
        app.refresh_ms = 5000
        app.api = mock.Mock()
        app.api.get_json.return_value = {"version": 7, "import_status": {"status": "succeeded"}}
        app.load_source_context = mock.Mock(return_value={"source": "codex", "limits": {"ok": True}})
        app.load_rows = mock.Mock()
        app.set_checked_status = mock.Mock()
        app.render_source_context = mock.Mock()
        app.render_rows = mock.Mock()
        app._ui = lambda callback: callback()
        app.last_source_context_refresh = {"codex": 100.0}
        request = {"source": "codex", "query": {"limit": 20, "source": "codex"}}

        with mock.patch.object(mini_client.time, "monotonic", return_value=105.0):
            app.poll_once(request)

        app.load_source_context.assert_called_once_with(request)
        app.load_rows.assert_not_called()
        app.render_source_context.assert_called_once_with({"source": "codex", "limits": {"ok": True}})
        app.set_checked_status.assert_called_once()
        self.assertEqual(app.last_source_context_refresh["codex"], 105.0)

    def test_changed_poll_refreshes_rows_and_source_context_immediately(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.data_version = 6
        app.refresh_ms = 5000
        app.api = mock.Mock()
        app.api.get_json.return_value = {"version": 7, "import_status": {"status": "succeeded"}}
        app.load_source_context = mock.Mock(return_value={"source": "codex", "limits": {"ok": True}})
        app.load_rows = mock.Mock(return_value=[{"thread_id": "thread-1"}])
        app.render_rows = mock.Mock()
        app._ui = lambda callback: callback()
        app.last_source_context_refresh = {"codex": 199.0}
        request = {"source": "codex", "query": {"limit": 20, "source": "codex"}}

        with mock.patch.object(mini_client.time, "monotonic", return_value=200.0):
            app.poll_once(request)

        app.load_source_context.assert_called_once_with(request)
        app.load_rows.assert_called_once_with(request)
        app.render_rows.assert_called_once_with(
            [{"thread_id": "thread-1"}],
            7,
            {"source": "codex", "limits": {"ok": True}},
            {"status": "succeeded"},
            None,
        )

    def test_stale_usage_limit_fallback_uses_request_source(self):
        snapshot = {
            "ok": True,
            "windows": [{"display_name": "Codex", "label": "5h", "remaining_percent": 93}],
        }
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.active_source = "opencode"
        app.last_usage_limits = {"codex": snapshot}

        stale = app.cached_usage_limits_or_error("timed out", source="codex")

        self.assertTrue(stale["ok"])
        self.assertTrue(stale["stale"])
        self.assertEqual(stale["stale_error"], "timed out")

    def test_disabled_settings_save_does_not_overwrite(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.settings_after_id = "pending"
        app.settings_save_enabled = False

        with mock.patch.object(mini_client, "save_mini_settings") as save:
            app.save_settings_now()

        self.assertIsNone(app.settings_after_id)
        save.assert_not_called()

    def test_settings_save_waits_until_startup_is_ready(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.closed = False
        app.settings_after_id = None
        app.settings_save_enabled = True
        app.settings_save_ready = False

        app.schedule_settings_save()
        with mock.patch.object(mini_client, "save_mini_settings") as save:
            app.save_settings_now()

        self.assertIsNone(app.settings_after_id)
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
