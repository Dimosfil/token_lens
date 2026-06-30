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
            ) or (
              feedback_log_body like '%"type":"response.created"%'
            ) or (
              feedback_log_body like '%"type":"response.in_progress"%'
            ) or (
              feedback_log_body like '%"type":"response.completed"%'
            ) or (
              feedback_log_body like '%response.completed%'
            ) or (
              feedback_log_body like '%post sampling token usage%'
            )
            order by id
            """
        )
        yield from rows
    finally:
        source.close()


def iter_log_rows_after(source_path: str, last_id: int = 0) -> Iterator[sqlite3.Row]:
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        rows = source.execute(
            """
            select id, ts, thread_id, feedback_log_body
            from logs
            where id > ?
            order by id
            """,
            [last_id],
        )
        yield from rows
    finally:
        source.close()


def latest_log_id(source_path: str) -> int:
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    try:
        row = source.execute("select coalesce(max(id), 0) from logs").fetchone()
        return int(row[0] if row else 0)
    finally:
        source.close()
