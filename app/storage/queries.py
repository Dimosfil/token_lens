from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3
import time

from app.storage.payloads import compact_event_payload, decode_json
from app.storage.query_params import (
    BUCKETS,
    CUSTOM_RANGE,
    DEFAULT_BUCKET,
    DEFAULT_RANGE,
    MAX_BUCKETS,
    RANGE_SECONDS,
    SEPARATE_TASK_RANGES,
    TASK_MODE_AGGREGATE,
    TASK_MODE_SEPARATE,
    TIME_MODE_LOCAL,
    normalize_bucket,
    normalize_range,
    normalize_task_mode,
    normalize_time_mode,
)


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def _range_clause(range_key: str = "", start_ts: int | None = None, end_ts: int | None = None):
    if range_key == "all":
        return "", []
    if range_key == CUSTOM_RANGE and start_ts is not None and end_ts is not None:
        lower, upper = sorted((int(start_ts), int(end_ts)))
        return "where ts >= ? and ts <= ?", [lower, upper]
    if range_key == CUSTOM_RANGE:
        range_key = DEFAULT_RANGE
    seconds = RANGE_SECONDS[normalize_range(range_key)]
    return "where ts >= ?", [int(time.time()) - seconds]


def _and_clause(where: str, clause: str) -> str:
    return f"{where} and {clause}" if where else f"where {clause}"


def _source_clause(where: str, params: list, source: str = "") -> tuple[str, list]:
    if source in {"codex", "opencode"}:
        where = _and_clause(where, "source = ?")
        params.append(source)
    return where, params


def _bucket_expr(bucket: str = "day", time_mode: str = TIME_MODE_LOCAL) -> str:
    normalized_time_mode = normalize_time_mode(time_mode)
    return BUCKETS[normalized_time_mode].get(bucket, BUCKETS[normalized_time_mode]["day"])


def _bucket_day_expr(bucket: str, period_expr: str) -> str:
    if bucket == "month":
        return f"{period_expr} || '-01'"
    return f"substr({period_expr}, 1, 10)"


def _trim_bucket_rows(rows: list[dict], range_key: str, bucket: str) -> list[dict]:
    if normalize_range(range_key) == CUSTOM_RANGE:
        return rows
    max_buckets = MAX_BUCKETS.get((normalize_range(range_key), bucket))
    if not max_buckets or len(rows) <= max_buckets:
        return rows
    return rows[-max_buckets:]


def _shift_month(dt: datetime, months: int) -> datetime:
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    return dt.replace(year=year, month=month)


def _expected_periods(range_key: str, bucket: str, time_mode: str = TIME_MODE_LOCAL) -> list[str]:
    if normalize_range(range_key) == CUSTOM_RANGE:
        return []
    count = MAX_BUCKETS.get((normalize_range(range_key), bucket))
    if not count:
        return []

    now = time.time()
    tz = timezone.utc if normalize_time_mode(time_mode) == "utc" else None
    if bucket == "hour":
        end = datetime.fromtimestamp(now, tz).replace(minute=0, second=0, microsecond=0)
        return [
            (end - timedelta(hours=offset)).strftime("%Y-%m-%d %H:00")
            for offset in range(count - 1, -1, -1)
        ]
    if bucket == "day":
        end = datetime.fromtimestamp(now, tz).replace(hour=0, minute=0, second=0, microsecond=0)
        return [
            (end - timedelta(days=offset)).date().isoformat()
            for offset in range(count - 1, -1, -1)
        ]
    if bucket == "month":
        end = datetime.fromtimestamp(now, tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return [
            _shift_month(end, -offset).strftime("%Y-%m")
            for offset in range(count - 1, -1, -1)
        ]
    return []


def _empty_bucket_row(period: str, bucket: str) -> dict:
    day = f"{period}-01" if bucket == "month" else period[:10]
    return {
        "period": period,
        "day": day,
        "turns": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_output_tokens": 0,
        "total_tokens": 0,
        "total_tokens_per_call": 0,
        "estimated_cost": 0,
    }


def _fill_bucket_rows(rows: list[dict], range_key: str, bucket: str, time_mode: str = TIME_MODE_LOCAL) -> list[dict]:
    periods = _expected_periods(range_key, bucket, time_mode)
    if not periods:
        return _trim_bucket_rows(rows, range_key, bucket)

    by_period = {row["period"]: row for row in rows}
    return [by_period.get(period, _empty_bucket_row(period, bucket)) for period in periods]


def summary(con: sqlite3.Connection, range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    if source == "opencode":
        return opencode_summary(con, range_key, start_ts, end_ts)

    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
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
        select source, ts_iso, thread_id, thread_name, turn_id, response_id, status, model, total_tokens,
               input_tokens, output_tokens, reasoning_output_tokens
        from turns
        {where}
        order by total_tokens desc
        limit 10
        """,
        params,
    ).fetchall()
    return {"summary": dict(row), "top_turns": rows_to_dicts(top)}


def opencode_summary(
    con: sqlite3.Connection,
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
):
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, "opencode")
    scoped_latest = f"""
        with ranked as (
            select turns.*,
                   row_number() over (
                       partition by thread_id
                       order by ts desc, source_log_id desc
                   ) as row_rank
            from turns
            {where}
        )
        select *
        from ranked
        where row_rank = 1
    """
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
        from ({scoped_latest})
        """,
        params,
    ).fetchone()
    top = con.execute(
        f"""
        select source, ts_iso, thread_id, thread_name, turn_id, response_id, status, model, total_tokens,
               input_tokens, output_tokens, reasoning_output_tokens
        from ({scoped_latest})
        order by total_tokens desc
        limit 10
        """,
        params,
    ).fetchall()
    return {"summary": dict(row), "top_turns": rows_to_dicts(top)}


def daily(
    con: sqlite3.Connection,
    range_key: str = "",
    bucket: str = "day",
    start_ts: int | None = None,
    end_ts: int | None = None,
    source: str = "",
    time_mode: str = TIME_MODE_LOCAL,
):
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
    normalized_bucket = normalize_bucket(bucket, range_key)
    period_expr = _bucket_expr(normalized_bucket, time_mode)
    day_expr = _bucket_day_expr(normalized_bucket, period_expr)
    rows = rows_to_dicts(con.execute(
        f"""
        select {period_expr} as period,
               min({day_expr}) as day,
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
    return _fill_bucket_rows(rows, range_key, normalized_bucket, time_mode)


def turns(con: sqlite3.Connection, limit: int, model: str = "", range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    params = []
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
    if model:
        where = _and_clause(where, "model = ?")
        params.append(model)
    params.append(limit)
    return rows_to_dicts(con.execute(
        f"""
        select source, source_log_id, ts, ts_iso, day, thread_id, thread_name, turn_id, response_id,
               submission_id, status, model,
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


def tasks(con: sqlite3.Connection, limit: int | None, range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    if source == "opencode":
        return opencode_tasks(con, limit, range_key, start_ts, end_ts)

    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
    limit_clause = ""
    if limit is not None:
        limit_clause = "limit ?"
        params.append(limit)
    return rows_to_dicts(con.execute(
        f"""
        select min(ts_iso) as started_at,
               max(ts_iso) as finished_at,
               max(ts) - min(ts) as elapsed_seconds,
               max(source) as source,
               min(source_log_id) as first_source_log_id,
               max(source_log_id) as last_source_log_id,
               thread_id,
               max(thread_name) as thread_name,
               turn_id,
               group_concat(distinct submission_id) as submission_ids,
               group_concat(distinct response_id) as response_ids,
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
        {limit_clause}
        """,
        params,
    ).fetchall())


def opencode_tasks(
    con: sqlite3.Connection,
    limit: int | None,
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
):
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, "opencode")
    limit_clause = ""
    if limit is not None:
        limit_clause = "limit ?"
        params.append(limit)
    return rows_to_dicts(con.execute(
        f"""
        with scoped as (
            select *
            from turns
            {where}
        ),
        ranked as (
            select scoped.*,
                   row_number() over (
                       partition by thread_id
                       order by ts desc, source_log_id desc
                   ) as row_rank
            from scoped
        ),
        aggregates as (
            select min(ts_iso) as started_at,
                   max(ts_iso) as finished_at,
                   max(ts) - min(ts) as elapsed_seconds,
                   min(source_log_id) as first_source_log_id,
                   max(source_log_id) as last_source_log_id,
                   thread_id,
                   group_concat(distinct submission_id) as submission_ids,
                   group_concat(distinct response_id) as response_ids,
                   group_concat(distinct model) as models,
                   group_concat(distinct status) as statuses,
                   group_concat(distinct reasoning_effort) as efforts,
                   count(*) as model_calls
            from scoped
            group by thread_id
        )
        select aggregates.started_at,
               aggregates.finished_at,
               aggregates.elapsed_seconds,
               'opencode' as source,
               aggregates.first_source_log_id,
               aggregates.last_source_log_id,
               aggregates.thread_id,
               ranked.thread_name,
               ranked.turn_id,
               aggregates.submission_ids,
               aggregates.response_ids,
               aggregates.models,
               aggregates.statuses,
               aggregates.efforts,
               aggregates.model_calls,
               ranked.input_tokens,
               ranked.cached_input_tokens,
               ranked.non_cached_input_tokens,
               ranked.output_tokens,
               ranked.reasoning_output_tokens,
               ranked.total_tokens,
               cast(round(ranked.total_tokens * 1.0 / aggregates.model_calls, 0) as integer) as total_tokens_per_call,
               ranked.estimated_cost
        from aggregates
        join ranked on ranked.thread_id = aggregates.thread_id and ranked.row_rank = 1
        order by ranked.ts desc
        {limit_clause}
        """,
        params,
    ).fetchall())


def task_buckets(
    con: sqlite3.Connection,
    range_key: str = "",
    bucket: str = "day",
    start_ts: int | None = None,
    end_ts: int | None = None,
    source: str = "",
    time_mode: str = TIME_MODE_LOCAL,
):
    normalized_bucket = normalize_bucket(bucket, range_key)
    period_expr = _bucket_expr(normalized_bucket, time_mode)
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
    rows = rows_to_dicts(con.execute(
        f"""
        select {period_expr} as period,
               min(ts_iso) as started_at,
               max(ts_iso) as finished_at,
               max(ts) - min(ts) as elapsed_seconds,
               min(ts) as bucket_start_ts,
               max(ts) as bucket_end_ts,
               count(distinct thread_id || ':' || turn_id) as tasks,
               count(*) as model_calls,
               group_concat(distinct model) as models,
               group_concat(distinct status) as statuses,
               group_concat(distinct reasoning_effort) as efforts,
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
        group by period
        order by period desc
        """,
        params,
    ).fetchall())
    return rows


def bucket_tasks(
    con: sqlite3.Connection,
    period: str,
    bucket: str = "day",
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
    source: str = "",
    time_mode: str = TIME_MODE_LOCAL,
):
    normalized_bucket = normalize_bucket(bucket, range_key)
    period_expr = _bucket_expr(normalized_bucket, time_mode)
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
    where = _and_clause(where, f"{period_expr} = ?")
    params.append(period)
    return rows_to_dicts(con.execute(
        f"""
        select min(ts_iso) as started_at,
               max(ts_iso) as finished_at,
               max(ts) - min(ts) as elapsed_seconds,
               min(source_log_id) as first_source_log_id,
               max(source_log_id) as last_source_log_id,
               thread_id,
               max(thread_name) as thread_name,
               turn_id,
               group_concat(distinct submission_id) as submission_ids,
               group_concat(distinct response_id) as response_ids,
               group_concat(distinct model) as models,
               group_concat(distinct status) as statuses,
               group_concat(distinct reasoning_effort) as efforts,
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
        """,
        params,
    ).fetchall())


def task_detail(con: sqlite3.Connection, thread_id: str, turn_id: str):
    rows = rows_to_dicts(con.execute(
        """
        select source_log_id, ts, ts_iso, day, thread_id, thread_name, turn_id, response_id,
               submission_id, status, model, reasoning_effort, input_tokens,
               cached_input_tokens, non_cached_input_tokens, output_tokens,
               reasoning_output_tokens, total_tokens, estimated_cost,
               request_json, response_json, event_json
        from turns
        where thread_id = ? and turn_id = ?
        order by ts, source_log_id
        """,
        [thread_id, turn_id],
    ).fetchall())
    if not rows:
        return {"task": None, "calls": []}

    for row in rows:
        row["request"] = decode_json(row.pop("request_json"))
        row["response"] = decode_json(row.pop("response_json"))
        row["event"] = compact_event_payload(decode_json(row.pop("event_json")))
        row["raw_event_captured"] = row["event"] is not None

    task = {
        "started_at": rows[0]["ts_iso"],
        "finished_at": rows[-1]["ts_iso"],
        "elapsed_seconds": rows[-1]["ts"] - rows[0]["ts"],
        "thread_id": rows[0]["thread_id"],
        "thread_name": rows[0]["thread_name"],
        "turn_id": rows[0]["turn_id"],
        "submission_ids": sorted({row["submission_id"] for row in rows if row["submission_id"]}),
        "response_ids": [row["response_id"] for row in rows if row["response_id"]],
        "models": sorted({row["model"] for row in rows if row["model"]}),
        "statuses": sorted({row["status"] for row in rows if row["status"]}),
        "model_calls": len(rows),
        "raw_event_calls": sum(1 for row in rows if row["raw_event_captured"]),
        "input_tokens": sum(row["input_tokens"] for row in rows),
        "cached_input_tokens": sum(row["cached_input_tokens"] for row in rows),
        "non_cached_input_tokens": sum(row["non_cached_input_tokens"] for row in rows),
        "output_tokens": sum(row["output_tokens"] for row in rows),
        "reasoning_output_tokens": sum(row["reasoning_output_tokens"] for row in rows),
        "total_tokens": sum(row["total_tokens"] for row in rows),
        "estimated_cost": sum(row["estimated_cost"] for row in rows),
    }
    task["raw_event_captured"] = task["raw_event_calls"] == task["model_calls"]
    task["total_tokens_per_call"] = round(task["total_tokens"] / task["model_calls"]) if task["model_calls"] else 0
    return {"task": task, "calls": rows}


def models(con: sqlite3.Connection, range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
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
               cast(round(avg(reasoning_output_tokens), 0) as integer) as avg_reasoning_output_tokens,
               sum(estimated_cost) as estimated_cost
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
    raw = con.execute(
        """
        select count(*) as raw_logs,
               coalesce(max(source_log_id), 0) as latest_raw_log_id,
               coalesce(max(ts), 0) as latest_raw_log_ts
        from raw_logs
        """
    ).fetchone()
    state.update(dict(raw))
    return state


def dashboard(
    con: sqlite3.Connection,
    model: str = "",
    range_key: str = "",
    bucket: str = "day",
    task_mode: str = TASK_MODE_AGGREGATE,
    start_ts: int | None = None,
    end_ts: int | None = None,
    source: str = "",
    time_mode: str = TIME_MODE_LOCAL,
):
    normalized_task_mode = normalize_task_mode(task_mode, range_key)
    normalized_time_mode = normalize_time_mode(time_mode)
    return {
        "state": data_state(con),
        "summary": summary(con, range_key, start_ts, end_ts, source),
        "daily": daily(con, range_key, bucket, start_ts, end_ts, source, normalized_time_mode),
        "turns": turns(con, 150, model, range_key, start_ts, end_ts, source),
        "task_mode": normalized_task_mode,
        "task_modes": {
            "requested": task_mode or TASK_MODE_AGGREGATE,
            "active": normalized_task_mode,
            "separate_available": normalize_range(range_key) in SEPARATE_TASK_RANGES,
        },
        "tasks": (
            tasks(con, None, range_key, start_ts, end_ts, source)
            if normalized_task_mode == TASK_MODE_SEPARATE
            else task_buckets(con, range_key, bucket, start_ts, end_ts, source, normalized_time_mode)
        ),
        "models": models(con, range_key, start_ts, end_ts, source),
        "time_mode": normalized_time_mode,
    }
