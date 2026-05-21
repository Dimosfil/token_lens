from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from app.api.handlers import parse_limit
from app.services import analytics_service
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
            "started_at", "finished_at", "first_source_log_id", "last_source_log_id",
            "thread_id", "thread_name", "turn_id", "submission_ids", "response_ids",
            "models", "statuses", "model_calls", "input_tokens",
            "cached_input_tokens", "non_cached_input_tokens", "output_tokens",
            "reasoning_output_tokens", "total_tokens", "total_tokens_per_call",
            "estimated_cost",
        }, set(tasks[0]))
        self.assertLessEqual({
            "model", "finished_at", "turns", "statuses", "total_tokens",
            "avg_total_tokens", "total_tokens_per_call", "avg_input_tokens",
            "avg_cached_input_tokens", "avg_non_cached_input_tokens",
            "avg_output_tokens", "avg_reasoning_output_tokens", "estimated_cost",
        }, set(models[0]))
        self.assertEqual(set(dashboard), {"state", "summary", "daily", "turns", "tasks", "models"})

    def test_service_state_includes_import_observability(self):
        original_load_config = analytics_service.load_config
        try:
            analytics_service.load_config = lambda: {"analytics_db": self.db_path}
            state = analytics_service.data_state()
            dashboard = analytics_service.dashboard()
        finally:
            analytics_service.load_config = original_load_config

        self.assertIn("import_status", state)
        self.assertIn("import_status", dashboard)
        self.assertIn("import_status", dashboard["state"])
        self.assertLessEqual({
            "status", "started_at", "completed_at", "duration_seconds", "stats", "error",
        }, set(state["import_status"]))

    def test_limit_parsing_falls_back_and_clamps(self):
        self.assertEqual(parse_limit({"limit": ["bad"]}, default=25, maximum=50), 25)
        self.assertEqual(parse_limit({"limit": ["0"]}, default=25, maximum=50), 1)
        self.assertEqual(parse_limit({"limit": ["5000"]}, default=25, maximum=50), 50)


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
            '"status":"completed","model":"gpt-5","usage":{'
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


if __name__ == "__main__":
    unittest.main()
