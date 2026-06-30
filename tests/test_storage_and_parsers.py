from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from app.sources.codex.parser import (
    compact_json,
    estimate_cost,
    parse_response_event,
    parse_usage_row,
    response_output_payload,
)
from app.sources.opencode.parser import (
    first_usage,
    first_value,
    int_value,
    parse_opencode_db_message,
    parse_opencode_event,
    parse_opencode_jsonl_record,
    stable_source_log_id,
    timestamp_seconds,
)
from app.storage.connection import connect
from app.storage.repositories import (
    get_opencode_import_state,
    insert_raw_log,
    latest_raw_log_id,
    set_latest_raw_log_id,
    set_opencode_import_state,
    upsert_turn,
)
from app.storage.schema import init_db


def row_fixture(**overrides):
    now = int(time.time())
    row = {
        "source_log_id": 1,
        "source": "codex",
        "response_id": None,
        "status": "completed",
        "ts": now,
        "ts_iso": "2026-06-19T00:00:00+00:00",
        "day": "2026-06-19",
        "thread_id": "thread-1",
        "thread_name": "Thread",
        "turn_id": "turn-1",
        "submission_id": "sub-1",
        "model": "gpt-5",
        "reasoning_effort": "medium",
        "input_tokens": 10,
        "cached_input_tokens": 3,
        "non_cached_input_tokens": 7,
        "output_tokens": 5,
        "reasoning_output_tokens": 1,
        "total_tokens": 15,
        "estimated_cost": 0.0,
        "request_json": None,
        "response_json": None,
        "event_json": None,
        "imported_at": "2026-06-19T00:00:00+00:00",
    }
    row.update(overrides)
    return row


class CodexParserUnitTests(unittest.TestCase):
    def test_compact_json_and_response_output_payload(self):
        self.assertIsNone(compact_json({}))
        self.assertEqual(compact_json({"text": "привет"}), '{"text":"привет"}')
        self.assertEqual(response_output_payload({"output": ["done"]}), ["done"])
        self.assertEqual(response_output_payload({"output_text": "done"}), "done")
        self.assertEqual(response_output_payload({"content": "done"}), "done")
        self.assertIsNone(response_output_payload({}))

    def test_estimate_cost_uses_cached_and_non_cached_prices(self):
        row = {
            "model": "gpt-5",
            "non_cached_input_tokens": 100,
            "cached_input_tokens": 50,
            "output_tokens": 25,
        }
        prices = {"gpt-5": {"input": 2.0, "cached_input": 0.5, "output": 8.0}}

        self.assertEqual(estimate_cost(row, prices), (100 * 2.0 + 50 * 0.5 + 25 * 8.0) / 1_000_000)
        self.assertEqual(estimate_cost({**row, "model": "missing"}, prices), 0)

    def test_usage_parser_recomputes_cached_tokens_from_non_cached_tokens(self):
        body = (
            'instrument_name="codex.turn.token_usage" model=gpt-5 '
            'thread.id=thread-1 turn.id=turn-1 submission.id="sub-1" '
            "codex.turn.token_usage.input_tokens=100 "
            "codex.turn.token_usage.cached_input_tokens=99 "
            "codex.turn.token_usage.non_cached_input_tokens=30 "
            "codex.turn.token_usage.output_tokens=20 "
            "codex.turn.token_usage.total_tokens=120"
        )

        row = parse_usage_row(1, 1_700_000_000, None, body, {"thread-1": "Thread"}, {})

        self.assertIsNotNone(row)
        self.assertEqual(row["cached_input_tokens"], 70)
        self.assertEqual(row["non_cached_input_tokens"], 30)
        self.assertEqual(row["thread_name"], "Thread")
        self.assertEqual(row["response_id"], "codex-usage:thread-1:turn-1:gpt-5")

    def test_usage_parser_accepts_current_rows_without_instrument_name(self):
        body = (
            "session_loop{thread_id=thread-1}:submission_dispatch{otel.name=\"op.dispatch.user_input\"}:"
            "turn{otel.name=\"session_task.turn\" thread.id=thread-1 turn.id=turn-1 "
            "model=gpt-5.5 codex.turn.reasoning_effort=medium "
            "codex.turn.token_usage.input_tokens=742224 "
            "codex.turn.token_usage.cached_input_tokens=570880 "
            "codex.turn.token_usage.non_cached_input_tokens=171344 "
            "codex.turn.token_usage.output_tokens=1320 "
            "codex.turn.token_usage.reasoning_output_tokens=512 "
            "codex.turn.token_usage.total_tokens=743544}:session_task.run"
        )

        row = parse_usage_row(1, 1_700_000_000, "thread-1", body, {}, {})

        self.assertIsNotNone(row)
        self.assertEqual(row["model"], "gpt-5.5")
        self.assertEqual(row["input_tokens"], 742224)
        self.assertEqual(row["cached_input_tokens"], 570880)
        self.assertEqual(row["non_cached_input_tokens"], 171344)
        self.assertEqual(row["response_id"], "codex-usage:thread-1:turn-1:gpt-5.5")

    def test_usage_parser_accepts_post_sampling_usage_estimate(self):
        body = (
            "session_loop{thread_id=thread-1}:submission_dispatch{otel.name=\"op.dispatch.user_input\" "
            "submission.id=\"sub-1\"}:turn{otel.name=\"session_task.turn\" thread.id=thread-1 "
            "turn.id=turn-1 model=gpt-5.5 codex.turn.reasoning_effort=high}:"
            "session_task.run:run_turn: post sampling token usage turn_id=turn-1 "
            "total_usage_tokens=45007 auto_compact_scope_tokens=45007 "
            "estimated_token_count=Some(50203) auto_compact_scope_limit=244800 "
            "full_context_window_limit_reached=false token_limit_reached=false"
        )

        row = parse_usage_row(1, 1_700_000_000, "thread-1", body, {"thread-1": "Thread"}, {})

        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "estimated")
        self.assertEqual(row["thread_name"], "Thread")
        self.assertEqual(row["input_tokens"], 45007)
        self.assertEqual(row["output_tokens"], 0)
        self.assertEqual(row["total_tokens"], 45007)
        self.assertEqual(row["response_id"], "codex-estimate:thread-1:turn-1:gpt-5.5")
        self.assertIn('"estimated_token_count":50203', row["event_json"])

    def test_usage_parser_rejects_token_usage_text_inside_response_output(self):
        body = (
            "session_loop{thread_id=thread-real}:submission_dispatch{otel.name=\"op.dispatch.user_input\"}:"
            "turn{otel.name=\"session_task.turn\" thread.id=thread-real turn.id=turn-real "
            "model=gpt-5.5 codex.turn.reasoning_effort=high}:session_task.run:"
            "run_sampling_request{turn_id=turn-real model=gpt-5.5}:"
            "response.completed output=\"tests\\\\test_storage_and_parsers.py:115: "
            "\\\"codex.turn.token_usage.input_tokens=742224 \\\"\\n"
            "tests\\\\test_storage_and_parsers.py:120: "
            "\\\"codex.turn.token_usage.total_tokens=743544\\\"\""
        )

        row = parse_usage_row(1, 1_700_000_000, "thread-real", body, {}, {})

        self.assertIsNone(row)

    def test_usage_parser_rejects_quoted_trace_usage_inside_response_output(self):
        body = (
            "session_loop{thread_id=thread-real}:submission_dispatch{otel.name=\"op.dispatch.user_input\"}:"
            "turn{otel.name=\"session_task.turn\" thread.id=thread-real turn.id=turn-real "
            "model=gpt-5.5 codex.turn.reasoning_effort=high}:session_task.run:"
            "response.output=\"session_loop{thread_id=old-thread}:submission_dispatch{otel.name=\\\"op.dispatch.user_input\\\"}:"
            "turn{otel.name=\\\"session_task.turn\\\" thread.id=old-thread turn.id=old-turn "
            "model=gpt-5.4-mini codex.turn.token_usage.input_tokens=10457 "
            "codex.turn.token_usage.output_tokens=79 codex.turn.token_usage.total_tokens=10536}\""
        )

        row = parse_usage_row(1, 1_700_000_000, "thread-real", body, {}, {})

        self.assertIsNone(row)

    def test_usage_parser_rejects_post_sampling_usage_inside_response_output(self):
        body = (
            "session_loop{thread_id=thread-real}:submission_dispatch{otel.name=\"op.dispatch.user_input\"}:"
            "turn{otel.name=\"session_task.turn\" thread.id=thread-real turn.id=turn-real "
            "model=gpt-5.5 codex.turn.reasoning_effort=high}:session_task.run:"
            "response.completed output=\"session_loop{thread_id=old-thread}:submission_dispatch{otel.name=\\\"op.dispatch.user_input\\\"}:"
            "turn{otel.name=\\\"session_task.turn\\\" thread.id=old-thread turn.id=old-turn "
            "model=gpt-5.5}:session_task.run:run_turn: post sampling token usage "
            "total_usage_tokens=45007 auto_compact_scope_tokens=45007\""
        )

        row = parse_usage_row(1, 1_700_000_000, "thread-real", body, {}, {})

        self.assertIsNone(row)

    def test_synthetic_usage_response_id_deduplicates_reimported_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "analytics.sqlite")
            init_db(db_path)
            con = connect(db_path)
            try:
                first = row_fixture(
                    source_log_id=10,
                    response_id="codex-usage:thread-1:turn-1:gpt-5",
                    total_tokens=100,
                )
                second = row_fixture(
                    source_log_id=11,
                    response_id="codex-usage:thread-1:turn-1:gpt-5",
                    total_tokens=100,
                )
                upsert_turn(con, first)
                upsert_turn(con, second)
                con.commit()
                rows = con.execute("select source_log_id, total_tokens from turns").fetchall()
            finally:
                con.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_log_id"], 11)
        self.assertEqual(rows[0]["total_tokens"], 100)

    def test_response_event_parser_requires_thread_turn_and_model(self):
        valid = (
            'thread.id=thread-1 turn.id=turn-1 '
            '{"type":"response.completed","response":{"id":"resp-1","status":"completed",'
            '"model":"gpt-5","usage":{"input_tokens":2,"output_tokens":3}}}'
        )
        invalid_json = 'thread.id=thread-1 turn.id=turn-1 {"type":"response.completed",'
        missing_model = 'thread.id=thread-1 turn.id=turn-1 {"type":"response.completed","response":{"id":"resp-1"}}'

        row = parse_response_event(2, 1_700_000_000, None, valid, {}, {})

        self.assertIsNotNone(row)
        self.assertEqual(row["response_id"], "resp-1")
        self.assertEqual(row["total_tokens"], 5)
        self.assertIsNone(parse_response_event(3, 1_700_000_000, None, invalid_json, {}, {}))
        self.assertIsNone(parse_response_event(4, 1_700_000_000, None, missing_model, {}, {}))

    def test_response_event_parser_rejects_completed_without_usage(self):
        body = (
            'thread.id=thread-1 turn.id=turn-1 '
            '{"type":"response.completed","response":{"id":"resp-1",'
            '"status":"completed","model":"gpt-5"}}'
        )

        row = parse_response_event(2, 1_700_000_000, None, body, {}, {})

        self.assertIsNone(row)


class OpenCodeParserUnitTests(unittest.TestCase):
    def test_nested_value_and_usage_helpers(self):
        payload = {"a": [{"b": {"session_id": "s1", "usage": {"input_tokens": "3", "output_tokens": "4"}}}]}

        self.assertEqual(int_value("5"), 5)
        self.assertEqual(int_value("bad", 7), 7)
        self.assertEqual(first_value(payload, ("session_id",)), "s1")
        self.assertEqual(first_usage(payload), {"input_tokens": "3", "output_tokens": "4"})

    def test_stable_source_log_id_is_deterministic_negative_integer(self):
        payload = {"session": "s", "message": "m", "usage": {"total_tokens": 1}}

        first_id = stable_source_log_id(payload)
        second_id = stable_source_log_id(dict(reversed(list(payload.items()))))

        self.assertEqual(first_id, second_id)
        self.assertLess(first_id, 0)

    def test_timestamp_seconds_accepts_seconds_milliseconds_and_iso(self):
        self.assertEqual(timestamp_seconds({"timestamp": 1_700_000_000}), 1_700_000_000)
        self.assertEqual(timestamp_seconds({"timestamp": 1_700_000_000_000}), 1_700_000_000)
        self.assertEqual(timestamp_seconds({"timestamp": "2026-06-19T00:00:00+00:00"}), 1_781_827_200)

    def test_opencode_parser_rejects_empty_usage(self):
        self.assertIsNone(parse_opencode_event({"usage": {"total_tokens": 0}}, {}))

    def test_opencode_db_message_normalizes_assistant_tokens(self):
        row = parse_opencode_db_message({
            "_rowid": 1,
            "id": "message-1",
            "session_id": "session-1",
            "time_created": 1_700_000_000_000,
            "session_title": "DeepSeek task",
            "session_directory": None,
            "data": json.dumps({
                "role": "assistant",
                "modelID": "deepseek/deepseek-chat",
                "variant": "chat",
                "finish": "completed",
                "time": {"created": 1_700_000_001_000},
                "tokens": {
                    "input": 100,
                    "output": 25,
                    "total": 125,
                    "reasoning": 5,
                    "cache": {"read": 40},
                },
                "cost": 0.0012,
            }),
        }, {})

        self.assertIsNotNone(row)
        self.assertEqual(row["source"], "opencode")
        self.assertEqual(row["response_id"], "opencode:message-1")
        self.assertEqual(row["thread_id"], "session-1")
        self.assertEqual(row["thread_name"], "DeepSeek task")
        self.assertEqual(row["model"], "deepseek/deepseek-chat")
        self.assertEqual(row["cached_input_tokens"], 40)
        self.assertEqual(row["non_cached_input_tokens"], 60)
        self.assertEqual(row["reasoning_output_tokens"], 5)
        self.assertEqual(row["estimated_cost"], 0.0012)

    def test_opencode_jsonl_record_normalizes_token_tracker_entry(self):
        row = parse_opencode_jsonl_record({
            "type": "tokens",
            "sessionId": "session-2",
            "messageId": "message-2",
            "model": "deepseek/deepseek-reasoner",
            "input": 12,
            "output": 8,
            "reasoning": 3,
            "cacheRead": 4,
            "_ts": 1_700_000_000_000,
        }, {"deepseek/deepseek-reasoner": {"input": 1.0, "cached_input": 0.1, "output": 2.0}})

        self.assertIsNotNone(row)
        self.assertEqual(row["response_id"], "opencode:message-2")
        self.assertEqual(row["thread_id"], "session-2")
        self.assertEqual(row["total_tokens"], 20)
        self.assertEqual(row["cached_input_tokens"], 4)
        self.assertEqual(row["non_cached_input_tokens"], 8)
        self.assertGreater(row["estimated_cost"], 0)


class StorageRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "analytics.sqlite")
        init_db(self.db_path)
        self.con = connect(self.db_path)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_upsert_turn_backfills_payloads_for_matching_usage_row(self):
        upsert_turn(self.con, row_fixture())
        event_json = json.dumps({"type": "response.completed", "response": {"id": "resp-1"}})

        upsert_turn(self.con, row_fixture(
            source_log_id=2,
            response_id="resp-1",
            request_json='{"input":"hi"}',
            response_json='{"output":"done"}',
            event_json=event_json,
        ))
        self.con.commit()

        rows = self.con.execute("select * from turns").fetchall()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_log_id"], 1)
        self.assertEqual(rows[0]["response_id"], "resp-1")
        self.assertEqual(rows[0]["request_json"], '{"input":"hi"}')
        self.assertEqual(rows[0]["event_json"], event_json)

    def test_raw_log_insert_updates_latest_cursor_once(self):
        inserted = insert_raw_log(self.con, {
            "id": 10,
            "ts": 1_700_000_000,
            "thread_id": "thread-1",
            "feedback_log_body": "body",
        })
        duplicate = insert_raw_log(self.con, {
            "id": 10,
            "ts": 1_700_000_000,
            "thread_id": "thread-1",
            "feedback_log_body": "body",
        })

        self.assertTrue(inserted)
        self.assertFalse(duplicate)
        self.assertEqual(latest_raw_log_id(self.con), 10)

        set_latest_raw_log_id(self.con, 42)
        self.assertEqual(latest_raw_log_id(self.con), 42)

    def test_opencode_import_state_round_trips(self):
        self.assertEqual(get_opencode_import_state(self.con), {
            "last_rowid": 0,
            "last_jsonl_offset": 0,
            "last_jsonl_size": 0,
        })

        set_opencode_import_state(self.con, 12, 345, 678)
        self.con.commit()

        self.assertEqual(get_opencode_import_state(self.con), {
            "last_rowid": 12,
            "last_jsonl_offset": 345,
            "last_jsonl_size": 678,
        })


if __name__ == "__main__":
    unittest.main()
