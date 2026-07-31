from __future__ import annotations

from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path

from app.services.import_service import repair_codex_usage_rows
from app.services.raw_log_retention import apply_raw_log_retention, retention_cutoff_day
from app.storage.connection import connect
from app.storage.repositories import insert_raw_log
from app.storage.schema import init_db


class RawLogRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "analytics.sqlite")
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cutoff_uses_calendar_months(self):
        now = datetime(2026, 7, 17, tzinfo=timezone.utc)

        self.assertEqual(retention_cutoff_day(1, now), "2026-07-01")
        self.assertEqual(retention_cutoff_day(2, now), "2026-06-01")

    def test_monthly_pass_clears_only_old_bodies_once(self):
        con = connect(self.db_path)
        try:
            insert_raw_log(con, self._raw_row(1, datetime(2026, 6, 30, tzinfo=timezone.utc), "old"))
            insert_raw_log(con, self._raw_row(2, datetime(2026, 7, 1, tzinfo=timezone.utc), "current"))
            con.commit()
        finally:
            con.close()

        now = datetime(2026, 7, 17, tzinfo=timezone.utc)
        result = apply_raw_log_retention(self.db_path, batch_size=1, now=now)
        repeated = apply_raw_log_retention(self.db_path, batch_size=1, now=now)

        con = connect(self.db_path)
        try:
            bodies = dict(con.execute(
                "select source_log_id, feedback_log_body from raw_logs order by source_log_id"
            ).fetchall())
        finally:
            con.close()

        self.assertTrue(result.applied)
        self.assertEqual(result.cleared_rows, 1)
        self.assertFalse(repeated.applied)
        self.assertEqual(bodies, {1: "", 2: "current"})

    def test_late_old_row_is_archived_without_body(self):
        con = connect(self.db_path)
        try:
            insert_raw_log(
                con,
                self._raw_row(1, datetime(2026, 6, 30, tzinfo=timezone.utc), "old"),
                raw_body_cutoff_day="2026-07-01",
            )
            con.commit()
            body = con.execute(
                "select feedback_log_body from raw_logs where source_log_id = 1"
            ).fetchone()[0]
        finally:
            con.close()

        self.assertEqual(body, "")

    def test_empty_retained_body_does_not_delete_turn_during_repair(self):
        con = connect(self.db_path)
        try:
            old = datetime(2026, 6, 30, tzinfo=timezone.utc)
            insert_raw_log(con, self._raw_row(1, old, ""))
            con.execute(
                """
                insert into turns (
                  source_log_id, source, response_id, status, ts, ts_iso, day,
                  thread_id, turn_id, model, total_tokens, imported_at
                ) values (?, 'codex', ?, 'completed', ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                [
                    1,
                    "codex-usage:1",
                    int(old.timestamp()),
                    old.isoformat(),
                    old.date().isoformat(),
                    "thread-1",
                    "turn-1",
                    "model-1",
                    old.isoformat(),
                ],
            )
            con.commit()

            repaired = repair_codex_usage_rows(con, {}, {})
            remaining = con.execute("select count(*) from turns").fetchone()[0]
        finally:
            con.close()

        self.assertEqual(repaired, 0)
        self.assertEqual(remaining, 1)

    @staticmethod
    def _raw_row(source_log_id: int, timestamp: datetime, body: str) -> dict:
        return {
            "id": source_log_id,
            "ts": int(timestamp.timestamp()),
            "thread_id": "thread-1",
            "thread_name": "Thread",
            "model": "model-1",
            "feedback_log_body": body,
        }


if __name__ == "__main__":
    unittest.main()
