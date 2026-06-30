from __future__ import annotations

from datetime import datetime, timezone
import sqlite3


DETAIL_DEFAULTS = {
    "source": "codex",
    "request_json": None,
    "response_json": None,
    "event_json": None,
}


def _row_get(row, key: str, default=None):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


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


def backfill_turn_request_payloads(con: sqlite3.Connection, rows: list[dict]) -> int:
    updated = 0
    imported_at = datetime.now(timezone.utc).isoformat()
    for row in rows:
        if not all(row.get(key) for key in ("thread_id", "turn_id", "model", "request_json")):
            continue
        cursor = con.execute(
            """
            update turns
            set request_json = ?,
                imported_at = ?
            where source = 'codex'
              and thread_id = ?
              and turn_id = ?
              and model = ?
              and coalesce(request_json, '') != ?
            """,
            [
                row["request_json"],
                imported_at,
                row["thread_id"],
                row["turn_id"],
                row["model"],
                row["request_json"],
            ],
        )
        updated += cursor.rowcount
    return updated


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


def latest_turn_source_log_id(con: sqlite3.Connection, source: str = "codex") -> int:
    row = con.execute(
        "select coalesce(max(source_log_id), 0) as latest_id from turns where source = ?",
        [source],
    ).fetchone()
    return int(row["latest_id"] if row else 0)


def get_codex_import_state(con: sqlite3.Connection) -> int:
    row = con.execute(
        "select last_scanned_source_log_id from codex_import_state where id = 1"
    ).fetchone()
    return int(row["last_scanned_source_log_id"] if row else 0)


def set_codex_import_state(con: sqlite3.Connection, source_log_id: int) -> None:
    con.execute(
        """
        insert into codex_import_state (id, last_scanned_source_log_id, updated_at)
        values (1, ?, ?)
        on conflict(id) do update set
          last_scanned_source_log_id = excluded.last_scanned_source_log_id,
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
          source_log_id, ts, ts_iso, day, thread_id, thread_name, model, feedback_log_body, archived_at
        ) values (
          :source_log_id, :ts, :ts_iso, :day, :thread_id, :thread_name, :model, :feedback_log_body, :archived_at
        )
        """,
        {
            "source_log_id": row["id"],
            "ts": ts,
            "ts_iso": dt.isoformat(),
            "day": dt.date().isoformat(),
            "thread_id": row["thread_id"],
            "thread_name": _row_get(row, "thread_name"),
            "model": _row_get(row, "model"),
            "feedback_log_body": row["feedback_log_body"] or "",
            "archived_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if cursor.rowcount > 0:
        set_latest_raw_log_id(con, row["id"])
    return cursor.rowcount > 0


def backfill_raw_log_display_fields(
    con: sqlite3.Connection,
    thread_names: dict[str, str],
    model_by_thread: dict[str, str] | None = None,
    limit: int = 2000,
) -> int:
    updated = 0
    model_by_thread = model_by_thread or {}
    rows = con.execute(
        """
        select thread_id
        from raw_logs
        where thread_id is not null
        group by thread_id
        order by max(source_log_id) desc
        limit ?
        """,
        [limit],
    ).fetchall()
    for row in rows:
        thread_id = row["thread_id"]
        thread_name = thread_names.get(thread_id)
        if not thread_name:
            continue
        cursor = con.execute(
            """
            update raw_logs
            set thread_name = ?,
                model = coalesce(model, ?)
            where thread_id = ?
              and (coalesce(thread_name, '') != ? or model is null)
            """,
            [thread_name, model_by_thread.get(thread_id), thread_id, thread_name],
        )
        updated += cursor.rowcount
    return updated


def backfill_turn_thread_names(
    con: sqlite3.Connection,
    thread_names: dict[str, str],
    source: str = "codex",
) -> int:
    updated = 0
    for thread_id, thread_name in thread_names.items():
        cursor = con.execute(
            """
            update turns
            set thread_name = ?
            where source = ?
              and thread_id = ?
              and coalesce(thread_name, '') != ?
            """,
            [thread_name, source, thread_id, thread_name],
        )
        updated += cursor.rowcount
    return updated


def upsert_codex_threads(con: sqlite3.Connection, rows: dict[str, dict]) -> int:
    imported_at = datetime.now(timezone.utc).isoformat()
    updated = 0
    for row in rows.values():
        if not row.get("thread_id"):
            continue
        payload = {
            "thread_id": row.get("thread_id"),
            "thread_name": row.get("thread_name"),
            "preview": row.get("preview"),
            "tokens_used": int(row.get("tokens_used") or 0),
            "model": row.get("model"),
            "reasoning_effort": row.get("reasoning_effort"),
            "cwd": row.get("cwd"),
            "updated_at": row.get("updated_at"),
            "recency_at": row.get("recency_at"),
            "imported_at": imported_at,
        }
        cursor = con.execute(
            """
            insert into codex_threads (
              thread_id, thread_name, preview, tokens_used, model, reasoning_effort,
              cwd, updated_at, recency_at, imported_at
            ) values (
              :thread_id, :thread_name, :preview, :tokens_used, :model, :reasoning_effort,
              :cwd, :updated_at, :recency_at, :imported_at
            )
            on conflict(thread_id) do update set
              thread_name = excluded.thread_name,
              preview = excluded.preview,
              tokens_used = excluded.tokens_used,
              model = excluded.model,
              reasoning_effort = excluded.reasoning_effort,
              cwd = excluded.cwd,
              updated_at = excluded.updated_at,
              recency_at = excluded.recency_at,
              imported_at = excluded.imported_at
            """,
            payload,
        )
        updated += cursor.rowcount
    return updated


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
