from __future__ import annotations

import sqlite3


def upsert_turn(con: sqlite3.Connection, row: dict) -> None:
    con.execute(
        """
        insert or replace into turns (
          source_log_id, response_id, status, ts, ts_iso, day, thread_id, thread_name, turn_id,
          submission_id, model, reasoning_effort, input_tokens,
          cached_input_tokens, non_cached_input_tokens, output_tokens,
          reasoning_output_tokens, total_tokens, estimated_cost, imported_at
        ) values (
          :source_log_id, :response_id, :status, :ts, :ts_iso, :day, :thread_id, :thread_name, :turn_id,
          :submission_id, :model, :reasoning_effort, :input_tokens,
          :cached_input_tokens, :non_cached_input_tokens, :output_tokens,
          :reasoning_output_tokens, :total_tokens, :estimated_cost, :imported_at
        )
        on conflict(response_id) do update set
          source_log_id = excluded.source_log_id,
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
          imported_at = excluded.imported_at
        """,
        row,
    )
