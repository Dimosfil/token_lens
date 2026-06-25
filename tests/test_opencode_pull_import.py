from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.services import import_service
from app.sources.opencode.parser import parse_opencode_db_message, parse_opencode_jsonl_record
from app.storage.connection import connect
from app.storage.repositories import get_opencode_import_state, set_opencode_import_state
from app.storage.schema import init_db


class OpenCodePullImportTests(unittest.TestCase):
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

    def test_opencode_import_state_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "analytics.sqlite")
            init_db(db_path)
            con = connect(db_path)
            try:
                self.assertEqual(get_opencode_import_state(con), {
                    "last_rowid": 0,
                    "last_jsonl_offset": 0,
                    "last_jsonl_size": 0,
                })

                set_opencode_import_state(con, 12, 345, 678)
                con.commit()

                self.assertEqual(get_opencode_import_state(con), {
                    "last_rowid": 12,
                    "last_jsonl_offset": 345,
                    "last_jsonl_size": 678,
                })
            finally:
                con.close()

    def test_opencode_reader_reads_sqlite_read_only(self):
        from app.sources.opencode.reader import iter_messages_after

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "opencode.sqlite"
            con = sqlite3.connect(db_path)
            try:
                con.execute("create table session (id text primary key, title text, directory text)")
                con.execute(
                    "create table message (id text primary key, session_id text, time_created integer, data text)"
                )
                con.execute("insert into session values ('session-1', 'Title', '/repo')")
                con.execute(
                    "insert into message values ('message-1', 'session-1', 1700000000000, ?)",
                    [json.dumps({"role": "assistant", "tokens": {"input": 1, "output": 2}})],
                )
                con.commit()
            finally:
                con.close()

            rows = list(iter_messages_after(str(db_path), 0))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "message-1")
        self.assertEqual(rows[0]["session_title"], "Title")

    def test_opencode_import_resets_rowid_when_source_db_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            analytics_db = str(root / "analytics.sqlite")
            source_db = root / "opencode.sqlite"
            init_db(analytics_db)
            con = sqlite3.connect(source_db)
            try:
                con.execute("create table session (id text primary key, title text, directory text)")
                con.execute(
                    "create table message (id text primary key, session_id text, time_created integer, data text)"
                )
                con.execute("insert into session values ('session-1', 'Today chat', '/repo')")
                con.execute(
                    "insert into message values ('message-1', 'session-1', 1782366903029, ?)",
                    [json.dumps({
                        "role": "assistant",
                        "modelID": "deepseek-v4-pro",
                        "time": {"created": 1782366903029},
                        "tokens": {"input": 10, "output": 5, "total": 15},
                    })],
                )
                con.commit()
            finally:
                con.close()

            target = connect(analytics_db)
            try:
                set_opencode_import_state(target, 999, 0, 0)
                target.commit()
            finally:
                target.close()

            with mock.patch.object(import_service, "load_config", return_value={
                "analytics_db": analytics_db,
                "opencode_db": str(source_db),
                "opencode_tokens_jsonl": "",
                "model_prices_per_million": {},
            }):
                stats = import_service.import_opencode_sources()

            target = connect(analytics_db)
            try:
                state = get_opencode_import_state(target)
                row = target.execute(
                    "select thread_name, day, total_tokens from turns where source = 'opencode'"
                ).fetchone()
            finally:
                target.close()

        self.assertEqual(stats.imported, 1)
        self.assertEqual(state["last_rowid"], 1)
        self.assertEqual(dict(row), {"thread_name": "Today chat", "day": "2026-06-25", "total_tokens": 15})


if __name__ == "__main__":
    unittest.main()
