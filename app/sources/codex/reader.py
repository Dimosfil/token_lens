from __future__ import annotations

import sqlite3
from collections.abc import Iterator


def iter_usage_log_rows(source_path: str) -> Iterator[sqlite3.Row]:
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        rows = source.execute(
            """
            select id, ts, thread_id, feedback_log_body
            from logs
            where (
              feedback_log_body like '%codex.turn.token_usage%'
              and feedback_log_body like '%instrument_name="codex.turn.token_usage"%'
            ) or (
              feedback_log_body like '%"type":"response.created"%'
            ) or (
              feedback_log_body like '%"type":"response.in_progress"%'
            ) or (
              feedback_log_body like '%"type":"response.completed"%'
            )
            order by id
            """
        )
        yield from rows
    finally:
        source.close()
