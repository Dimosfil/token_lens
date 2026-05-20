from __future__ import annotations

import sqlite3
import time


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


RANGE_SECONDS = {
    "24h": 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
    "30d": 30 * 24 * 60 * 60,
    "365d": 365 * 24 * 60 * 60,
}

BUCKETS = {
    "hour": "strftime('%Y-%m-%d %H:00', ts, 'unixepoch', 'localtime')",
    "day": "day",
    "month": "substr(day, 1, 7)",
    "year": "substr(day, 1, 4)",
}


def _range_clause(range_key: str = ""):
    seconds = RANGE_SECONDS.get(range_key)
    if not seconds:
        return "", []
    return "where ts >= ?", [int(time.time()) - seconds]


def _and_clause(where: str, clause: str) -> str:
    return f"{where} and {clause}" if where else f"where {clause}"


def _bucket_expr(bucket: str = "day") -> str:
    return BUCKETS.get(bucket, BUCKETS["day"])


def summary(con: sqlite3.Connection, range_key: str = ""):
    where, params = _range_clause(range_key)
    row = con.execute(
        f"""
        select count(*) as turns,
               count(distinct thread_id) as threads,
               coalesce(sum(input_tokens), 0) as input_tokens,
               coalesce(sum(output_tokens), 0) as output_tokens,
               coalesce(sum(cached_input_tokens), 0) as cached_input_tokens,
               coalesce(sum(reasoning_output_tokens), 0) as reasoning_output_tokens,
               coalesce(sum(total_tokens), 0) as total_tokens,
               coalesce(sum(estimated_cost), 0) as estimated_cost,
               max(ts_iso) as latest_turn
        from turns
        {where}
        """,
        params,
    ).fetchone()
    top = con.execute(
        f"""
        select ts_iso, thread_id, thread_name, turn_id, response_id, status, model, total_tokens,
               input_tokens, output_tokens, reasoning_output_tokens
        from turns
        {where}
        order by total_tokens desc
        limit 10
        """,
        params,
    ).fetchall()
    return {"summary": dict(row), "top_turns": rows_to_dicts(top)}


def daily(con: sqlite3.Connection, range_key: str = "", bucket: str = "day"):
    where, params = _range_clause(range_key)
    period_expr = _bucket_expr(bucket)
    return rows_to_dicts(con.execute(
        f"""
        select {period_expr} as period,
               min(day) as day,
               count(*) as turns,
               sum(input_tokens) as input_tokens,
               sum(output_tokens) as output_tokens,
               sum(cached_input_tokens) as cached_input_tokens,
               sum(reasoning_output_tokens) as reasoning_output_tokens,
               sum(total_tokens) as total_tokens,
               cast(round(sum(total_tokens) * 1.0 / count(*), 0) as integer) as total_tokens_per_call,
               sum(estimated_cost) as estimated_cost
        from turns
        {where}
        group by period
        order by period
        """,
        params,
    ).fetchall())


def turns(con: sqlite3.Connection, limit: int, model: str = "", range_key: str = ""):
    params = []
    where, params = _range_clause(range_key)
    if model:
        where = _and_clause(where, "model = ?")
        params.append(model)
    params.append(limit)
    return rows_to_dicts(con.execute(
        f"""
        select ts_iso, day, thread_id, thread_name, turn_id, response_id, status, model,
               reasoning_effort, input_tokens, cached_input_tokens,
               non_cached_input_tokens, output_tokens,
               reasoning_output_tokens, total_tokens, estimated_cost
        from turns
        {where}
        order by ts desc
        limit ?
        """,
        params,
    ).fetchall())


def tasks(con: sqlite3.Connection, limit: int, range_key: str = ""):
    where, params = _range_clause(range_key)
    params.append(limit)
    return rows_to_dicts(con.execute(
        f"""
        select min(ts_iso) as started_at,
               max(ts_iso) as finished_at,
               thread_id,
               max(thread_name) as thread_name,
               turn_id,
               group_concat(distinct model) as models,
               group_concat(distinct status) as statuses,
               count(*) as model_calls,
               sum(input_tokens) as input_tokens,
               sum(cached_input_tokens) as cached_input_tokens,
               sum(non_cached_input_tokens) as non_cached_input_tokens,
               sum(output_tokens) as output_tokens,
               sum(reasoning_output_tokens) as reasoning_output_tokens,
               sum(total_tokens) as total_tokens,
               cast(round(sum(total_tokens) * 1.0 / count(*), 0) as integer) as total_tokens_per_call,
               sum(estimated_cost) as estimated_cost
        from turns
        {where}
        group by thread_id, turn_id
        order by max(ts) desc
        limit ?
        """,
        params,
    ).fetchall())


def models(con: sqlite3.Connection, range_key: str = ""):
    where, params = _range_clause(range_key)
    return rows_to_dicts(con.execute(
        f"""
        select model,
               max(ts_iso) as finished_at,
               count(*) as turns,
               group_concat(distinct status) as statuses,
               sum(total_tokens) as total_tokens,
               cast(round(avg(total_tokens), 0) as integer) as avg_total_tokens,
               cast(round(avg(total_tokens), 0) as integer) as total_tokens_per_call,
               cast(round(avg(input_tokens), 0) as integer) as avg_input_tokens,
               cast(round(avg(cached_input_tokens), 0) as integer) as avg_cached_input_tokens,
               cast(round(avg(non_cached_input_tokens), 0) as integer) as avg_non_cached_input_tokens,
               cast(round(avg(output_tokens), 0) as integer) as avg_output_tokens,
               cast(round(avg(reasoning_output_tokens), 0) as integer) as avg_reasoning_output_tokens
        from turns
        {where}
        group by model
        order by total_tokens desc
        """,
        params,
    ).fetchall())


def data_state(con: sqlite3.Connection):
    row = con.execute(
        """
        select count(*) as turns,
               coalesce(max(source_log_id), 0) as latest_source_log_id,
               coalesce(max(ts), 0) as latest_ts,
               coalesce(sum(total_tokens), 0) as total_tokens
        from turns
        """
    ).fetchone()
    state = dict(row)
    state["version"] = ":".join(str(state[key]) for key in (
        "turns",
        "latest_source_log_id",
        "latest_ts",
        "total_tokens",
    ))
    return state


def dashboard(con: sqlite3.Connection, model: str = "", range_key: str = "", bucket: str = "day"):
    return {
        "state": data_state(con),
        "summary": summary(con, range_key),
        "daily": daily(con, range_key, bucket),
        "turns": turns(con, 150, model, range_key),
        "tasks": tasks(con, 150, range_key),
        "models": models(con, range_key),
    }
