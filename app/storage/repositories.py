from __future__ import annotations

from datetime import datetime, timezone
import sqlite3


DETAIL_DEFAULTS = {
    "source": "codex",
    "request_json": None,
    "response_json": None,
    "event_json": None,
}


def upsert_turn(con: sqlite3.Connection, row: dict) -> None:
    row = {**DETAIL_DEFAULTS, **row}
    if row["event_json"]:
        cursor = con.execute(
            """
            update turns
            set response_id = :response_id,
                source = :source,
                status = :status,
                request_json = :request_json,
                response_json = :response_json,
                event_json = :event_json,
                imported_at = :imported_at
            where thread_id = :thread_id
              and turn_id = :turn_id
              and model = :model
              and input_tokens = :input_tokens
              and output_tokens = :output_tokens
              and total_tokens = :total_tokens
              and event_json is null
              and not exists (
                select 1 from turns existing
                where existing.response_id = :response_id
              )
            """,
            row,
        )
        if cursor.rowcount > 0:
            return

    con.execute(
        """
        insert or replace into turns (
          source_log_id, source, response_id, status, ts, ts_iso, day, thread_id, thread_name, turn_id,
          submission_id, model, reasoning_effort, input_tokens,
          cached_input_tokens, non_cached_input_tokens, output_tokens,
          reasoning_output_tokens, total_tokens, estimated_cost,
          request_json, response_json, event_json, imported_at
        ) values (
          :source_log_id, :source, :response_id, :status, :ts, :ts_iso, :day, :thread_id, :thread_name, :turn_id,
          :submission_id, :model, :reasoning_effort, :input_tokens,
          :cached_input_tokens, :non_cached_input_tokens, :output_tokens,
          :reasoning_output_tokens, :total_tokens, :estimated_cost,
          :request_json, :response_json, :event_json, :imported_at
        )
        on conflict(response_id) do update set
          source_log_id = excluded.source_log_id,
          source = excluded.source,
          status = excluded.status,
          ts = excluded.ts,
          ts_iso = excluded.ts_iso,
          day = excluded.day,
          thread_id = excluded.thread_id,
          thread_name = excluded.thread_name,
          turn_id = excluded.turn_id,
          submission_id = excluded.submission_id,
          model = excluded.model,
          reasoning_effort = excluded.reasoning_effort,
          input_tokens = excluded.input_tokens,
          cached_input_tokens = excluded.cached_input_tokens,
          non_cached_input_tokens = excluded.non_cached_input_tokens,
          output_tokens = excluded.output_tokens,
          reasoning_output_tokens = excluded.reasoning_output_tokens,
          total_tokens = excluded.total_tokens,
          estimated_cost = excluded.estimated_cost,
          request_json = excluded.request_json,
          response_json = excluded.response_json,
          event_json = excluded.event_json,
          imported_at = excluded.imported_at
        """,
        row,
    )


def latest_raw_log_id(con: sqlite3.Connection) -> int:
    state = con.execute(
        "select last_source_log_id from raw_log_archive_state where id = 1"
    ).fetchone()
    if state:
        return int(state["last_source_log_id"])
    row = con.execute("select coalesce(max(source_log_id), 0) as latest_id from raw_logs").fetchone()
    return int(row["latest_id"] if row else 0)


def set_latest_raw_log_id(con: sqlite3.Connection, source_log_id: int) -> None:
    con.execute(
        """
        insert into raw_log_archive_state (id, last_source_log_id, updated_at)
        values (1, ?, ?)
        on conflict(id) do update set
          last_source_log_id = excluded.last_source_log_id,
          updated_at = excluded.updated_at
        """,
        [int(source_log_id), datetime.now(timezone.utc).isoformat()],
    )


def insert_raw_log(con: sqlite3.Connection, row: dict) -> bool:
    ts = int(row["ts"])
    dt = datetime.fromtimestamp(ts, timezone.utc)
    cursor = con.execute(
        """
        insert or ignore into raw_logs (
          source_log_id, ts, ts_iso, day, thread_id, feedback_log_body, archived_at
        ) values (
          :source_log_id, :ts, :ts_iso, :day, :thread_id, :feedback_log_body, :archived_at
        )
        """,
        {
            "source_log_id": row["id"],
            "ts": ts,
            "ts_iso": dt.isoformat(),
            "day": dt.date().isoformat(),
            "thread_id": row["thread_id"],
            "feedback_log_body": row["feedback_log_body"] or "",
            "archived_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if cursor.rowcount > 0:
        set_latest_raw_log_id(con, row["id"])
    return cursor.rowcount > 0


def get_opencode_import_state(con: sqlite3.Connection) -> dict:
    row = con.execute(
        "select last_rowid, last_jsonl_offset, last_jsonl_size from opencode_import_state where id = 1"
    ).fetchone()
    if row:
        return dict(row)
    return {"last_rowid": 0, "last_jsonl_offset": 0, "last_jsonl_size": 0}


def set_opencode_import_state(
    con: sqlite3.Connection,
    last_rowid: int,
    last_jsonl_offset: int,
    last_jsonl_size: int = 0,
) -> None:
    con.execute(
        """
        insert into opencode_import_state (id, last_rowid, last_jsonl_offset, last_jsonl_size, updated_at)
        values (1, ?, ?, ?, ?)
        on conflict(id) do update set
          last_rowid = excluded.last_rowid,
          last_jsonl_offset = excluded.last_jsonl_offset,
          last_jsonl_size = excluded.last_jsonl_size,
          updated_at = excluded.updated_at
        """,
        [int(last_rowid), int(last_jsonl_offset), int(last_jsonl_size), datetime.now(timezone.utc).isoformat()],
    )
