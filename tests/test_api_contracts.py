from __future__ import annotations

import json
import queue
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from app.api.handlers import parse_limit
from app.services import analytics_service, codex_account_service, import_service
from app.services.import_service import import_usage_source
from app.sources.opencode.parser import parse_opencode_event
from app.sources.codex.parser import parse_response_event, parse_usage_row
from app.storage import queries
from app.storage.query_params import normalize_time_mode
from app.storage.connection import connect
from app.storage.repositories import upsert_turn
from app.storage.schema import init_db


def sample_turn(**overrides):
    ts = int(time.time()) - 60
    row = {
        "source_log_id": 1,
        "response_id": "resp-1",
        "status": "completed",
        "ts": ts,
        "ts_iso": "2026-05-21T00:00:00+00:00",
        "day": "2026-05-21",
        "thread_id": "thread-1",
        "thread_name": "Sample thread",
        "turn_id": "turn-1",
        "submission_id": "sub-1",
        "model": "gpt-5",
        "reasoning_effort": "medium",
        "input_tokens": 100,
        "cached_input_tokens": 25,
        "non_cached_input_tokens": 75,
        "output_tokens": 40,
        "reasoning_output_tokens": 8,
        "total_tokens": 140,
        "estimated_cost": 0.001,
        "imported_at": "2026-05-20T00:00:00+00:00",
    }
    row.update(overrides)
    return row


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "analytics.sqlite")
        init_db(self.db_path)
        con = connect(self.db_path)
        try:
            upsert_turn(con, sample_turn())
            upsert_turn(con, sample_turn(
                source_log_id=2,
                response_id="resp-2",
                ts=int(time.time()) - 30,
                ts_iso="2026-05-21T00:00:30+00:00",
                day="2026-05-21",
                thread_id="thread-2",
                thread_name="Second thread",
                turn_id="turn-2",
                model="gpt-5-mini",
                input_tokens=80,
                cached_input_tokens=10,
                non_cached_input_tokens=70,
                output_tokens=20,
                reasoning_output_tokens=4,
                total_tokens=100,
            ))
            con.commit()
        finally:
            con.close()

    def tearDown(self):
        codex_account_service.close_codex_account_client()
        self.tmp.cleanup()

    def test_query_response_shapes(self):
        con = connect(self.db_path)
        try:
            summary = queries.summary(con)
            state = queries.data_state(con)
            daily = queries.daily(con)
            turns = queries.turns(con, 10)
            tasks = queries.tasks(con, 10)
            models = queries.models(con)
            dashboard = queries.dashboard(con)
        finally:
            con.close()

        self.assertEqual(set(summary), {"summary", "top_turns"})
        self.assertLessEqual({
            "turns", "threads", "input_tokens", "output_tokens",
            "cached_input_tokens", "reasoning_output_tokens",
            "total_tokens", "estimated_cost", "latest_turn",
        }, set(summary["summary"]))
        self.assertLessEqual({
            "turns", "latest_source_log_id", "latest_ts", "total_tokens", "version",
            "raw_logs", "latest_raw_log_id", "latest_raw_log_ts",
        }, set(state))
        self.assertLessEqual({
            "period", "day", "turns", "input_tokens", "output_tokens",
            "cached_input_tokens", "reasoning_output_tokens", "total_tokens",
            "total_tokens_per_call", "estimated_cost",
        }, set(daily[0]))
        self.assertLessEqual({
            "source_log_id", "ts_iso", "day", "thread_id", "thread_name",
            "turn_id", "response_id", "submission_id", "status", "model", "reasoning_effort",
            "input_tokens", "cached_input_tokens", "non_cached_input_tokens",
            "output_tokens", "reasoning_output_tokens", "total_tokens",
            "estimated_cost",
        }, set(turns[0]))
        self.assertLessEqual({
            "period", "started_at", "finished_at", "bucket_start_ts", "bucket_end_ts",
            "elapsed_seconds", "tasks", "models", "statuses", "efforts", "model_calls", "input_tokens",
            "cached_input_tokens", "non_cached_input_tokens", "output_tokens",
            "reasoning_output_tokens", "total_tokens", "total_tokens_per_call",
            "estimated_cost",
        }, set(dashboard["tasks"][0]))
        self.assertLessEqual({
            "model", "finished_at", "turns", "statuses", "total_tokens",
            "avg_total_tokens", "total_tokens_per_call", "avg_input_tokens",
            "avg_cached_input_tokens", "avg_non_cached_input_tokens",
            "avg_output_tokens", "avg_reasoning_output_tokens", "estimated_cost",
        }, set(models[0]))
        self.assertEqual(set(dashboard), {"state", "summary", "daily", "turns", "task_mode", "task_modes", "tasks", "models", "time_mode"})
        self.assertEqual(dashboard["task_mode"], "aggregate")
        self.assertEqual(dashboard["time_mode"], "local")
        self.assertLessEqual({"requested", "active", "separate_available"}, set(dashboard["task_modes"]))

    def test_time_mode_defaults_to_local_and_keeps_utc_switch(self):
        self.assertEqual(normalize_time_mode(""), "local")
        self.assertEqual(normalize_time_mode("local"), "local")
        self.assertEqual(normalize_time_mode("utc"), "utc")
        self.assertEqual(normalize_time_mode("unexpected"), "local")
        self.assertIn("'localtime'", queries._bucket_expr("day", "local"))
        self.assertNotIn("'localtime'", queries._bucket_expr("day", "utc"))

    def test_codex_account_rate_limits_are_normalized(self):
        payload = codex_account_service._normalize_rate_limits({
            "rateLimits": {
                "limitId": "codex",
                "planType": "prolite",
                "primary": {"usedPercent": 9, "windowDurationMins": 300, "resetsAt": int(time.time()) + 60},
                "secondary": {"usedPercent": 15, "windowDurationMins": 10080, "resetsAt": int(time.time()) + 120},
                "credits": {"hasCredits": False, "unlimited": False, "balance": "0"},
            },
            "rateLimitsByLimitId": {
                "codex": {
                    "limitId": "codex",
                    "planType": "prolite",
                    "primary": {"usedPercent": 9, "windowDurationMins": 300, "resetsAt": int(time.time()) + 60},
                    "secondary": {"usedPercent": 15, "windowDurationMins": 10080, "resetsAt": int(time.time()) + 120},
                },
                "codex_bengalfox": {
                    "limitId": "codex_bengalfox",
                    "limitName": "GPT-5.3-Codex-Spark",
                    "planType": "prolite",
                    "primary": {"usedPercent": 0, "windowDurationMins": 300, "resetsAt": int(time.time()) + 60},
                    "secondary": {"usedPercent": 0, "windowDurationMins": 10080, "resetsAt": int(time.time()) + 120},
                },
            },
        })

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["source"], "codex_app_server")
        self.assertEqual(payload["limit_id"], "codex")
        self.assertEqual(payload["plan_type"], "prolite")
        self.assertEqual(payload["limit_ids"], ["codex", "codex_bengalfox"])
        self.assertEqual(len(payload["groups"]), 2)
        self.assertEqual(len(payload["windows"]), 4)
        self.assertEqual(payload["windows"][0]["label"], "5h")
        self.assertEqual(payload["windows"][0]["remaining_percent"], 91)
        self.assertEqual(payload["windows"][1]["label"], "weekly")
        self.assertEqual(payload["windows"][1]["remaining_percent"], 85)
        self.assertEqual(payload["windows"][2]["display_name"], "GPT-5.3-Codex-Spark")
        self.assertEqual(payload["windows"][2]["remaining_percent"], 100)

    def test_codex_account_command_prefers_configured_override(self):
        self.assertEqual(
            codex_account_service._resolve_codex_command({"codex_app_server_command": "C:\\tools\\codex.cmd"}),
            "C:\\tools\\codex.cmd",
        )

    def test_codex_account_limits_reject_windowsapps_launcher_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            alias = Path(tmp) / "WindowsApps" / "codex.exe"
            alias.parent.mkdir(parents=True)
            alias.write_text("", encoding="utf-8")

            payload = codex_account_service.read_usage_limits({
                "codex_app_server_command": str(alias),
            })

        self.assertFalse(payload["ok"])
        self.assertIn("avoid WindowsApps aliases", payload["error"])

    def test_codex_account_persistent_client_reuses_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = Path(tmp) / "codex.cmd"
            command.write_text("", encoding="utf-8")
            fake_popen = FakeCodexPopen()
            config = {
                "codex_app_server_command": str(command),
                "codex_rate_limits_cache_seconds": 0,
            }

            with (
                mock.patch.object(codex_account_service.subprocess, "Popen", fake_popen),
                mock.patch.object(codex_account_service.subprocess, "run"),
            ):
                first = codex_account_service.read_usage_limits(config)
                second = codex_account_service.read_usage_limits(config)
                codex_account_service.close_codex_account_client()

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(fake_popen.call_count, 1)
        self.assertEqual(fake_popen.processes[0].read_requests, 2)
        self.assertEqual(fake_popen.processes[0].initialize_requests, 1)

    def test_codex_account_persistent_client_restarts_exited_process(self):
        fake_popen = FakeCodexPopen()
        client = codex_account_service.CodexAppServerClient("codex.cmd")

        with (
            mock.patch.object(codex_account_service.subprocess, "Popen", fake_popen),
            mock.patch.object(codex_account_service.subprocess, "run"),
        ):
            first = client.request_rate_limits(3)
            fake_popen.processes[0].returncode = 1
            second = client.request_rate_limits(3)
            client.close()

        self.assertEqual(first["result"]["rateLimits"]["limitId"], "codex")
        self.assertEqual(second["result"]["rateLimits"]["limitId"], "codex")
        self.assertEqual(fake_popen.call_count, 2)

    def test_codex_account_global_client_cleanup_stops_process_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = Path(tmp) / "codex.cmd"
            command.write_text("", encoding="utf-8")
            fake_popen = FakeCodexPopen()
            config = {
                "codex_app_server_command": str(command),
                "codex_rate_limits_cache_seconds": 0,
            }

            with (
                mock.patch.object(codex_account_service.subprocess, "Popen", fake_popen),
                mock.patch.object(codex_account_service.subprocess, "run"),
            ):
                payload = codex_account_service.read_usage_limits(config)
                codex_account_service.close_codex_account_client()

        self.assertTrue(payload["ok"])
        self.assertEqual(fake_popen.call_count, 1)
        self.assertTrue(fake_popen.processes[0].killed)

    def test_codex_account_stop_process_uses_taskkill_tree_on_windows(self):
        class FakeProcess:
            pid = 1234

            def poll(self):
                return 1

            def kill(self):
                raise AssertionError("taskkill should handle the Windows process tree")

        with (
            mock.patch.object(codex_account_service.os, "name", "nt"),
            mock.patch.object(codex_account_service.subprocess, "run") as run,
        ):
            codex_account_service._stop_process(FakeProcess())

        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["taskkill", "/F", "/T", "/PID", "1234"])

    def test_task_detail_returns_calls_and_payloads(self):
        con = connect(self.db_path)
        try:
            detail = queries.task_detail(con, "thread-1", "turn-1")
        finally:
            con.close()

        self.assertLessEqual({
            "started_at", "finished_at", "thread_id", "thread_name", "turn_id",
            "elapsed_seconds", "submission_ids", "response_ids", "models", "statuses", "model_calls",
            "raw_event_calls", "raw_event_captured",
            "input_tokens", "cached_input_tokens", "non_cached_input_tokens",
            "output_tokens", "reasoning_output_tokens", "total_tokens",
            "total_tokens_per_call", "estimated_cost",
        }, set(detail["task"]))
        self.assertEqual(len(detail["calls"]), 1)
        self.assertLessEqual({"request", "response", "event", "raw_event_captured"}, set(detail["calls"][0]))
        self.assertFalse(detail["calls"][0]["raw_event_captured"])

    def test_task_detail_compacts_large_raw_event_response_metadata(self):
        raw_event = {
            "type": "response.completed",
            "sequence_number": 1,
            "response": {
                "id": "resp-large",
                "status": "completed",
                "model": "gpt-5",
                "instructions": "large instructions" * 100,
                "tools": [{"name": "large-tool", "schema": "x" * 1000}],
                "input": [{"role": "user", "content": "hello"}],
                "output": [{"type": "message", "content": "done"}],
                "usage": {"total_tokens": 140},
            },
        }
        con = connect(self.db_path)
        try:
            upsert_turn(con, sample_turn(
                source_log_id=3,
                response_id="resp-large",
                event_json=json.dumps(raw_event),
            ))
            con.commit()
            detail = queries.task_detail(con, "thread-1", "turn-1")
        finally:
            con.close()

        event = next(call["event"] for call in detail["calls"] if call["response_id"] == "resp-large")
        self.assertTrue(event["compacted"])
        self.assertEqual(event["response"]["id"], "resp-large")
        self.assertEqual(event["response"]["usage"], {"total_tokens": 140})
        self.assertNotIn("instructions", event["response"])
        self.assertNotIn("tools", event["response"])
        self.assertIn("instructions", event["omitted_response_fields"])

    def test_service_state_includes_import_observability(self):
        original_load_config = analytics_service.load_config
        original_read_usage_limits = analytics_service.read_usage_limits
        try:
            analytics_service.load_config = lambda: {"analytics_db": self.db_path}
            analytics_service.read_usage_limits = lambda _config: {
                "ok": True,
                "source": "codex_app_server",
                "windows": [],
            }
            state = analytics_service.data_state()
            dashboard = analytics_service.dashboard()
        finally:
            analytics_service.load_config = original_load_config
            analytics_service.read_usage_limits = original_read_usage_limits

        self.assertIn("import_status", state)
        self.assertIn("source_warnings", state)
        self.assertIn("import_status", dashboard)
        self.assertIn("source_warnings", dashboard)
        self.assertIn("import_status", dashboard["state"])
        self.assertIn("source_warnings", dashboard["state"])
        self.assertIn("usage_limits", dashboard)
        self.assertLessEqual({
            "status", "started_at", "completed_at", "duration_seconds", "stats", "error",
        }, set(state["import_status"]))

    def test_dashboard_tasks_follow_selected_range(self):
        old_ts = int(time.time()) - (10 * 24 * 60 * 60)
        con = connect(self.db_path)
        try:
            upsert_turn(con, sample_turn(
                source_log_id=3,
                response_id="resp-old",
                ts=old_ts,
                ts_iso="2026-05-11T00:00:00+00:00",
                day="2026-05-11",
                thread_id="thread-old",
                thread_name="Old thread",
                turn_id="turn-old",
                total_tokens=77,
            ))
            con.commit()

            dashboard = queries.dashboard(con, range_key="1h")
        finally:
            con.close()

        self.assertEqual(dashboard["summary"]["summary"]["turns"], 2)
        self.assertEqual(sum(row["tasks"] for row in dashboard["tasks"]), 2)
        self.assertNotIn("thread-old", {row["thread_id"] for row in dashboard["turns"]})

    def test_dashboard_separate_task_mode_is_limited_to_short_ranges(self):
        old_ts = int(time.time()) - (10 * 24 * 60 * 60)
        con = connect(self.db_path)
        try:
            upsert_turn(con, sample_turn(
                source_log_id=3,
                response_id="resp-old",
                ts=old_ts,
                ts_iso="2026-05-11T00:00:00+00:00",
                day="2026-05-11",
                thread_id="thread-old",
                thread_name="Old thread",
                turn_id="turn-old",
                total_tokens=77,
            ))
            con.commit()

            separate = queries.dashboard(con, range_key="24h", task_mode="separate")
            forced_aggregate = queries.dashboard(con, range_key="7d", task_mode="separate")
        finally:
            con.close()

        self.assertEqual(separate["task_mode"], "separate")
        self.assertTrue(separate["task_modes"]["separate_available"])
        self.assertEqual({row["thread_id"] for row in separate["tasks"]}, {"thread-1", "thread-2"})
        self.assertEqual(forced_aggregate["task_mode"], "aggregate")
        self.assertFalse(forced_aggregate["task_modes"]["separate_available"])
        self.assertIn("period", forced_aggregate["tasks"][0])

    def test_codex_empty_in_progress_rows_are_hidden_from_usage_views(self):
        con = connect(self.db_path)
        try:
            upsert_turn(con, sample_turn(
                source_log_id=3,
                response_id="resp-empty-progress",
                status="in_progress",
                ts=int(time.time()),
                ts_iso="2026-05-21T00:01:00+00:00",
                day="2026-05-21",
                thread_id="thread-progress",
                thread_name="Progress placeholder",
                turn_id="turn-progress",
                input_tokens=0,
                cached_input_tokens=0,
                non_cached_input_tokens=0,
                output_tokens=0,
                reasoning_output_tokens=0,
                total_tokens=0,
                event_json='{"type":"response.in_progress"}',
            ))
            upsert_turn(con, sample_turn(
                source_log_id=4,
                response_id="resp-empty-completed",
                status="completed",
                ts=int(time.time()) + 1,
                ts_iso="2026-05-21T00:02:00+00:00",
                day="2026-05-21",
                thread_id="thread-empty-completed",
                thread_name="Empty completed placeholder",
                turn_id="turn-empty-completed",
                input_tokens=0,
                cached_input_tokens=0,
                non_cached_input_tokens=100,
                output_tokens=0,
                reasoning_output_tokens=0,
                total_tokens=0,
            ))
            upsert_turn(con, sample_turn(
                source_log_id=5,
                response_id="resp-inconsistent-completed",
                status="completed",
                ts=int(time.time()) + 2,
                ts_iso="2026-05-21T00:03:00+00:00",
                day="2026-05-21",
                thread_id="thread-inconsistent-completed",
                thread_name="Inconsistent completed placeholder",
                turn_id="turn-inconsistent-completed",
                input_tokens=100,
                cached_input_tokens=30,
                non_cached_input_tokens=70,
                output_tokens=50,
                reasoning_output_tokens=10,
                total_tokens=2,
            ))
            con.commit()

            summary = queries.summary(con)["summary"]
            turns = queries.turns(con, 10)
            tasks = queries.tasks(con, 10)
            state = queries.data_state(con)
        finally:
            con.close()

        self.assertEqual(summary["turns"], 2)
        self.assertEqual(state["turns"], 2)
        self.assertNotIn("thread-progress", {row["thread_id"] for row in turns})
        self.assertNotIn("thread-progress", {row["thread_id"] for row in tasks})
        self.assertNotIn("thread-empty-completed", {row["thread_id"] for row in turns})
        self.assertNotIn("thread-empty-completed", {row["thread_id"] for row in tasks})
        self.assertNotIn("thread-inconsistent-completed", {row["thread_id"] for row in turns})
        self.assertNotIn("thread-inconsistent-completed", {row["thread_id"] for row in tasks})

    def test_codex_tasks_include_raw_only_threads_without_usage(self):
        now = int(time.time())
        con = connect(self.db_path)
        try:
            con.execute(
                """
                insert into raw_logs (
                  source_log_id, ts, ts_iso, day, thread_id, thread_name, model, feedback_log_body, archived_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    10,
                    now + 10,
                    "2026-06-26T08:20:00+00:00",
                    "2026-06-26",
                    "thread-raw-only",
                    "Update ht,en",
                    "gpt-5.5",
                    "thread.id=thread-raw-only turn.id=turn-raw model=gpt-5.5",
                    "2026-06-26T08:20:01+00:00",
                ],
            )
            con.commit()

            rows = queries.tasks(con, 10, source="codex")
        finally:
            con.close()

        raw_row = next(row for row in rows if row["thread_id"] == "thread-raw-only")
        self.assertEqual(raw_row["thread_name"], "Update ht,en")
        self.assertEqual(raw_row["statuses"], "usage-missing")
        self.assertEqual(raw_row["models"], "gpt-5.5")
        self.assertEqual(raw_row["has_usage"], 0)
        self.assertEqual(raw_row["model_calls"], 0)
        self.assertEqual(raw_row["raw_event_calls"], 1)
        self.assertIsNone(raw_row["total_tokens"])
        self.assertIsNone(raw_row["total_tokens_per_call"])

    def test_opencode_tasks_and_summary_sum_request_rows_per_chat(self):
        now = int(time.time())
        con = connect(self.db_path)
        try:
            for index, total_tokens in enumerate((1000, 1600, 2500), start=1):
                upsert_turn(con, sample_turn(
                    source_log_id=-100 - index,
                    source="opencode",
                    response_id=f"opencode:message-{index}",
                    ts=now + index,
                    ts_iso=f"2026-06-19T14:0{index}:00+00:00",
                    day="2026-06-19",
                    thread_id="opencode-session-1",
                    thread_name="One OpenCode chat",
                    turn_id=f"message-{index}",
                    model="deepseek-v4-pro",
                    input_tokens=10 * index,
                    cached_input_tokens=total_tokens - 100,
                    non_cached_input_tokens=10 * index,
                    output_tokens=70,
                    reasoning_output_tokens=30,
                    total_tokens=total_tokens,
                    estimated_cost=0.001 * index,
                ))
            con.commit()

            rows = queries.tasks(con, 10, source="opencode")
            summary = queries.summary(con, source="opencode")["summary"]
        finally:
            con.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["thread_id"], "opencode-session-1")
        self.assertEqual(rows[0]["thread_name"], "One OpenCode chat")
        self.assertEqual(rows[0]["model_calls"], 3)
        self.assertEqual(rows[0]["total_tokens"], 5100)
        self.assertEqual(rows[0]["total_tokens_per_call"], 1700)
        self.assertEqual(summary["turns"], 3)
        self.assertEqual(summary["threads"], 1)
        self.assertEqual(summary["total_tokens"], 5100)

    def test_bucket_tasks_returns_tasks_for_selected_period(self):
        con = connect(self.db_path)
        try:
            rows = queries.bucket_tasks(con, "2026-05-21", "day", time_mode="utc")
        finally:
            con.close()

        self.assertEqual({row["thread_id"] for row in rows}, {"thread-1", "thread-2"})
        self.assertLessEqual({
            "thread_id", "turn_id", "elapsed_seconds", "models", "statuses", "efforts", "model_calls",
            "total_tokens", "total_tokens_per_call",
        }, set(rows[0]))

    def test_limit_parsing_falls_back_and_clamps(self):
        self.assertEqual(parse_limit({"limit": ["bad"]}, default=25, maximum=50), 25)
        self.assertEqual(parse_limit({"limit": ["0"]}, default=25, maximum=50), 1)
        self.assertEqual(parse_limit({"limit": ["5000"]}, default=25, maximum=50), 50)

    def test_import_archives_every_raw_log_row(self):
        class Source:
            def __init__(self):
                self.rows = [
                    {
                        "id": 10,
                        "ts": int(time.time()) - 5,
                        "thread_id": "thread-raw",
                        "feedback_log_body": "unrecognized raw event",
                    },
                    {
                        "id": 11,
                        "ts": int(time.time()) - 4,
                        "thread_id": "thread-raw",
                        "feedback_log_body": (
                            'instrument_name="codex.turn.token_usage" model=gpt-5 '
                            'thread.id=thread-raw turn.id=turn-raw '
                            "codex.turn.token_usage.input_tokens=3 "
                            "codex.turn.token_usage.output_tokens=2 "
                            "codex.turn.token_usage.total_tokens=5"
                        ),
                    },
                ]

            def iter_rows(self):
                return iter(self.rows)

            def iter_rows_after(self, last_id=0):
                return (row for row in self.rows if row["id"] > last_id)

            def load_thread_names(self):
                return {}

        stats = import_usage_source(Source(), self.db_path, {})
        con = connect(self.db_path)
        try:
            raw_count = con.execute("select count(*) from raw_logs").fetchone()[0]
            raw_body = con.execute(
                "select feedback_log_body from raw_logs where source_log_id = 10"
            ).fetchone()[0]
        finally:
            con.close()

        self.assertEqual(stats.archived, 2)
        self.assertEqual(stats.imported, 1)
        self.assertEqual(raw_count, 2)
        self.assertEqual(raw_body, "unrecognized raw event")

    def test_codex_import_scans_only_rows_after_latest_imported_turn(self):
        class Source:
            def __init__(self):
                self.rows = [
                    {
                        "id": 1,
                        "ts": int(time.time()) - 5,
                        "thread_id": "thread-old",
                        "feedback_log_body": (
                            'instrument_name="codex.turn.token_usage" model=gpt-5 '
                            'thread.id=thread-old turn.id=turn-old '
                            "codex.turn.token_usage.input_tokens=1 "
                            "codex.turn.token_usage.output_tokens=1 "
                            "codex.turn.token_usage.total_tokens=2"
                        ),
                    },
                    {
                        "id": 3,
                        "ts": int(time.time()) - 4,
                        "thread_id": "thread-new",
                        "feedback_log_body": (
                            'instrument_name="codex.turn.token_usage" model=gpt-5 '
                            'thread.id=thread-new turn.id=turn-new '
                            "codex.turn.token_usage.input_tokens=3 "
                            "codex.turn.token_usage.output_tokens=2 "
                            "codex.turn.token_usage.total_tokens=5"
                        ),
                    },
                    {
                        "id": 4,
                        "ts": int(time.time()) - 3,
                        "thread_id": "thread-new",
                        "feedback_log_body": "unrecognized raw event",
                    },
                ]

            def iter_rows(self):
                raise AssertionError("full Codex scan should not run when incremental rows are available")

            def iter_rows_after(self, last_id=0):
                return (row for row in self.rows if row["id"] > last_id)

            def load_thread_names(self):
                return {}

        stats = import_usage_source(Source(), self.db_path, {})
        con = connect(self.db_path)
        try:
            imported = con.execute(
                "select count(*) from turns where thread_id = 'thread-new'"
            ).fetchone()[0]
        finally:
            con.close()

        self.assertEqual(stats.scanned, 2)
        self.assertEqual(stats.imported, 1)
        self.assertEqual(stats.skipped, 1)
        self.assertEqual(stats.archived, 3)
        self.assertEqual(imported, 1)

    def test_response_event_backfills_matching_usage_row_payloads(self):
        class Source:
            def __init__(self):
                self.rows = [
                    {
                        "id": 20,
                        "ts": int(time.time()) - 5,
                        "thread_id": "thread-merge",
                        "feedback_log_body": (
                            'instrument_name="codex.turn.token_usage" model=gpt-5 '
                            'thread.id=thread-merge turn.id=turn-merge submission.id="sub-merge" '
                            "codex.turn.token_usage.input_tokens=9 "
                            "codex.turn.token_usage.cached_input_tokens=4 "
                            "codex.turn.token_usage.output_tokens=6 "
                            "codex.turn.token_usage.total_tokens=15"
                        ),
                    },
                    {
                        "id": 21,
                        "ts": int(time.time()) - 4,
                        "thread_id": "thread-merge",
                        "feedback_log_body": (
                            'thread.id=thread-merge turn.id=turn-merge submission.id="sub-merge" '
                            '{"type":"response.completed","response":{"id":"resp-merge",'
                            '"status":"completed","model":"gpt-5","input":[{"role":"user","content":"inspect"}],'
                            '"output":[{"type":"message","content":[{"type":"output_text","text":"done"}]}],'
                            '"usage":{"input_tokens":9,"input_tokens_details":{"cached_tokens":4},'
                            '"output_tokens":6,"total_tokens":15}}}'
                        ),
                    },
                ]

            def iter_rows(self):
                return iter(self.rows)

            def iter_rows_after(self, last_id=0):
                return (row for row in self.rows if row["id"] > last_id)

            def load_thread_names(self):
                return {}

        stats = import_usage_source(Source(), self.db_path, {})
        con = connect(self.db_path)
        try:
            detail = queries.task_detail(con, "thread-merge", "turn-merge")
            row_count = con.execute(
                "select count(*) from turns where thread_id = 'thread-merge'"
            ).fetchone()[0]
        finally:
            con.close()

        self.assertEqual(stats.imported, 2)
        self.assertEqual(row_count, 1)
        self.assertEqual(detail["task"]["raw_event_calls"], 1)
        self.assertTrue(detail["task"]["raw_event_captured"])
        self.assertTrue(detail["calls"][0]["raw_event_captured"])
        self.assertEqual(detail["calls"][0]["response_id"], "resp-merge")
        self.assertIn("inspect", str(detail["calls"][0]["request"]))


class ImportConfigurationTests(unittest.TestCase):
    def test_codex_import_is_skipped_when_source_is_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            analytics_db = str(Path(tmp) / "analytics.sqlite")
            with mock.patch.object(
                import_service,
                "load_config",
                return_value={
                    "analytics_db": analytics_db,
                    "codex_logs_db": "",
                    "codex_session_index": "",
                    "model_prices_per_million": {},
                },
            ), mock.patch.object(import_service.LOGGER, "warning") as warning:
                stats = import_service.import_codex_logs()

        self.assertEqual(stats.scanned, 0)
        self.assertEqual(stats.imported, 0)
        warning.assert_called_once()


class ParserContractTests(unittest.TestCase):
    def test_usage_and_response_rows_share_common_fields(self):
        thread_names = {"thread-1": "Sample thread"}
        prices = {"gpt-5": {"input": 2, "cached_input": 1, "output": 8}}
        usage_body = (
            'instrument_name="codex.turn.token_usage" model=gpt-5 '
            'thread.id=thread-1 turn.id=turn-1 submission.id="sub-1" '
            "codex.turn.reasoning_effort=high "
            "codex.turn.token_usage.input_tokens=100 "
            "codex.turn.token_usage.cached_input_tokens=30 "
            "codex.turn.token_usage.non_cached_input_tokens=70 "
            "codex.turn.token_usage.output_tokens=50 "
            "codex.turn.token_usage.reasoning_output_tokens=10 "
            "codex.turn.token_usage.total_tokens=150"
        )
        response_body = (
            'thread.id=thread-1 turn.id=turn-1 submission.id="sub-1" '
            "codex.turn.reasoning_effort=high "
            '{"type":"response.completed","response":{"id":"resp-1",'
            '"status":"completed","model":"gpt-5","input":[{"role":"user","content":"hi"}],'
            '"output":[{"type":"message","content":[{"type":"output_text","text":"hello"}]}],"usage":{'
            '"input_tokens":100,"input_tokens_details":{"cached_tokens":30},'
            '"output_tokens":50,"output_tokens_details":{"reasoning_tokens":10},'
            '"total_tokens":150}}}'
        )

        usage_row = parse_usage_row(1, 1_700_000_000, None, usage_body, thread_names, prices)
        response_row = parse_response_event(2, 1_700_000_000, None, response_body, thread_names, prices)

        self.assertIsNotNone(usage_row)
        self.assertIsNotNone(response_row)
        for key in (
            "status", "ts_iso", "day", "thread_id", "thread_name", "turn_id",
            "submission_id", "model", "reasoning_effort", "input_tokens",
            "cached_input_tokens", "non_cached_input_tokens", "output_tokens",
            "reasoning_output_tokens", "total_tokens", "estimated_cost",
        ):
            self.assertEqual(usage_row[key], response_row[key])
        self.assertIn("hi", response_row["request_json"])
        self.assertIn("hello", response_row["response_json"])

    def test_empty_in_progress_response_event_is_not_usage(self):
        body = (
            'thread.id=thread-1 turn.id=turn-1 '
            '{"type":"response.in_progress","response":{"id":"resp-1",'
            '"status":"in_progress","model":"gpt-5"}}'
        )

        row = parse_response_event(1, 1_700_000_000, None, body, {}, {})

        self.assertIsNone(row)

    def test_empty_token_usage_row_is_not_usage(self):
        body = (
            'instrument_name="codex.turn.token_usage" model=gpt-5 '
            'thread.id=thread-1 turn.id=turn-1 '
            "codex.turn.token_usage.non_cached_input_tokens=100 "
            "codex.turn.token_usage.total_tokens=0"
        )

        row = parse_usage_row(1, 1_700_000_000, None, body, {}, {})

        self.assertIsNone(row)

    def test_inconsistent_token_usage_row_is_not_usage(self):
        body = (
            'instrument_name="codex.turn.token_usage" model=gpt-5 '
            'thread.id=thread-1 turn.id=turn-1 '
            "codex.turn.token_usage.input_tokens=100 "
            "codex.turn.token_usage.output_tokens=50 "
            "codex.turn.token_usage.total_tokens=2"
        )

        row = parse_usage_row(1, 1_700_000_000, None, body, {}, {})

        self.assertIsNone(row)

    def test_opencode_event_normalizes_to_turn_row(self):
        payload = {
            "source": "opencode",
            "timestamp": 1_700_000_000_000,
            "directory": "D:\\AI\\AiAnalytics\\token-lens",
            "event": {
                "type": "message.updated",
                "sessionID": "opencode-session-1",
                "messageID": "message-1",
                "message": {
                    "model": "deepseek/deepseek-chat",
                    "usage": {
                        "input_tokens": 120,
                        "input_tokens_details": {"cached_tokens": 20},
                        "output_tokens": 30,
                        "output_tokens_details": {"reasoning_tokens": 5},
                        "total_tokens": 150,
                    },
                },
            },
        }

        row = parse_opencode_event(payload, {})

        self.assertIsNotNone(row)
        self.assertLess(row["source_log_id"], 0)
        self.assertEqual(row["response_id"], "opencode:message-1")
        self.assertEqual(row["thread_id"], "opencode-session-1")
        self.assertEqual(row["turn_id"], "message-1")
        self.assertEqual(row["model"], "deepseek/deepseek-chat")
        self.assertEqual(row["input_tokens"], 120)
        self.assertEqual(row["cached_input_tokens"], 20)
        self.assertEqual(row["non_cached_input_tokens"], 100)
        self.assertEqual(row["output_tokens"], 30)
        self.assertEqual(row["reasoning_output_tokens"], 5)
        self.assertEqual(row["total_tokens"], 150)
        self.assertIn("message.updated", row["event_json"])

class FakeCodexPopen:
    def __init__(self):
        self.processes = []

    @property
    def call_count(self):
        return len(self.processes)

    def __call__(self, *args, **_kwargs):
        process = FakeCodexProcess(pid=1000 + len(self.processes))
        self.processes.append(process)
        return process


class FakeCodexProcess:
    def __init__(self, pid: int):
        self.pid = pid
        self.returncode = None
        self.killed = False
        self.initialize_requests = 0
        self.read_requests = 0
        self.stdout = FakeCodexStdout()
        self.stdin = FakeCodexStdin(self)

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9
        self.stdout.close()

    def wait(self, timeout=None):
        return self.returncode

    def handle_message(self, message: dict) -> None:
        message_id = message.get("id")
        method = message.get("method")
        if method == "initialize":
            self.initialize_requests += 1
            self.stdout.push({"id": message_id, "result": {}})
        elif method == "account/rateLimits/read":
            self.read_requests += 1
            self.stdout.push({
                "id": message_id,
                "result": {
                    "rateLimits": {
                        "limitId": "codex",
                        "planType": "prolite",
                        "primary": {
                            "usedPercent": 25,
                            "windowDurationMins": 300,
                            "resetsAt": int(time.time()) + 60,
                        },
                    },
                    "rateLimitsByLimitId": {},
                },
            })


class FakeCodexStdin:
    def __init__(self, process: FakeCodexProcess):
        self.process = process

    def write(self, text: str):
        message = json.loads(text)
        self.process.handle_message(message)

    def flush(self):
        pass


class FakeCodexStdout:
    def __init__(self):
        self.lines = queue.Queue()

    def __iter__(self):
        return self

    def __next__(self):
        line = self.lines.get(timeout=5)
        if line is None:
            raise StopIteration
        return line

    def push(self, message: dict) -> None:
        self.lines.put(json.dumps(message) + "\n")

    def close(self) -> None:
        self.lines.put(None)


if __name__ == "__main__":
    unittest.main()
