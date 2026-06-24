from __future__ import annotations

import json
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
        self.assertEqual(set(dashboard), {"state", "summary", "daily", "turns", "task_mode", "task_modes", "tasks", "models"})
        self.assertEqual(dashboard["task_mode"], "aggregate")
        self.assertLessEqual({"requested", "active", "separate_available"}, set(dashboard["task_modes"]))

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
        self.assertIn("import_status", dashboard)
        self.assertIn("import_status", dashboard["state"])
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

    def test_bucket_tasks_returns_tasks_for_selected_period(self):
        con = connect(self.db_path)
        try:
            rows = queries.bucket_tasks(con, "2026-05-21", "day")
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


if __name__ == "__main__":
    unittest.main()
