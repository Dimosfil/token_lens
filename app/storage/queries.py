from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sqlite3
import time


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def decode_json(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


DEFAULT_RANGE = "7d"
DEFAULT_BUCKET = "day"

RANGE_SECONDS = {
    "1h": 60 * 60,
    "24h": 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
    "30d": 30 * 24 * 60 * 60,
    "365d": 365 * 24 * 60 * 60,
}

BUCKET_SECONDS = {
    "hour": 60 * 60,
    "day": 24 * 60 * 60,
    "month": 30 * 24 * 60 * 60,
}

BUCKETS = {
    "hour": "strftime('%Y-%m-%d %H:00', ts, 'unixepoch', 'localtime')",
    "day": "day",
    "month": "substr(day, 1, 7)",
}

MAX_BUCKETS = {
    ("1h", "hour"): 1,
    ("24h", "hour"): 24,
    ("24h", "day"): 1,
    ("7d", "hour"): 7 * 24,
    ("7d", "day"): 7,
    ("30d", "hour"): 30 * 24,
    ("30d", "day"): 30,
    ("30d", "month"): 1,
    ("365d", "hour"): 365 * 24,
    ("365d", "day"): 365,
    ("365d", "month"): 12,
}


def normalize_range(range_key: str = "") -> str:
    return range_key if range_key in RANGE_SECONDS else DEFAULT_RANGE


def normalize_bucket(bucket: str = DEFAULT_BUCKET, range_key: str = DEFAULT_RANGE) -> str:
    range_seconds = RANGE_SECONDS[normalize_range(range_key)]
    bucket_seconds = BUCKET_SECONDS.get(bucket)
    if bucket_seconds and bucket_seconds <= range_seconds:
        return bucket
    return DEFAULT_BUCKET if BUCKET_SECONDS[DEFAULT_BUCKET] <= range_seconds else "hour"


def _range_clause(range_key: str = ""):
    seconds = RANGE_SECONDS[normalize_range(range_key)]
    return "where ts >= ?", [int(time.time()) - seconds]


def _and_clause(where: str, clause: str) -> str:
    return f"{where} and {clause}" if where else f"where {clause}"


def _bucket_expr(bucket: str = "day") -> str:
    return BUCKETS.get(bucket, BUCKETS["day"])


def _trim_bucket_rows(rows: list[dict], range_key: str, bucket: str) -> list[dict]:
    max_buckets = MAX_BUCKETS.get((normalize_range(range_key), bucket))
    if not max_buckets or len(rows) <= max_buckets:
        return rows
    return rows[-max_buckets:]


def _shift_month(dt: datetime, months: int) -> datetime:
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    return dt.replace(year=year, month=month)


def _expected_periods(range_key: str, bucket: str) -> list[str]:
    count = MAX_BUCKETS.get((normalize_range(range_key), bucket))
    if not count:
        return []

    now = time.time()
    if bucket == "hour":
        end = datetime.fromtimestamp(now).replace(minute=0, second=0, microsecond=0)
        return [
            (end - timedelta(hours=offset)).strftime("%Y-%m-%d %H:00")
            for offset in range(count - 1, -1, -1)
        ]
    if bucket == "day":
        end = datetime.fromtimestamp(now, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return [
            (end - timedelta(days=offset)).date().isoformat()
            for offset in range(count - 1, -1, -1)
        ]
    if bucket == "month":
        end = datetime.fromtimestamp(now, timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
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


def _fill_bucket_rows(rows: list[dict], range_key: str, bucket: str) -> list[dict]:
    periods = _expected_periods(range_key, bucket)
    if not periods:
        return _trim_bucket_rows(rows, range_key, bucket)

    by_period = {row["period"]: row for row in rows}
    return [by_period.get(period, _empty_bucket_row(period, bucket)) for period in periods]


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
    normalized_bucket = normalize_bucket(bucket, range_key)
    period_expr = _bucket_expr(normalized_bucket)
    rows = rows_to_dicts(con.execute(
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
    return _fill_bucket_rows(rows, range_key, normalized_bucket)


def turns(con: sqlite3.Connection, limit: int, model: str = "", range_key: str = ""):
    params = []
    where, params = _range_clause(range_key)
    if model:
        where = _and_clause(where, "model = ?")
        params.append(model)
    params.append(limit)
    return rows_to_dicts(con.execute(
        f"""
        select source_log_id, ts_iso, day, thread_id, thread_name, turn_id, response_id,
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


def tasks(con: sqlite3.Connection, limit: int, range_key: str = ""):
    where, params = _range_clause(range_key)
    params.append(limit)
    return rows_to_dicts(con.execute(
        f"""
        select min(ts_iso) as started_at,
               max(ts_iso) as finished_at,
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
        limit ?
        """,
        params,
    ).fetchall())


def task_detail(con: sqlite3.Connection, thread_id: str, turn_id: str):
    rows = rows_to_dicts(con.execute(
        """
        select source_log_id, ts_iso, day, thread_id, thread_name, turn_id, response_id,
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
        row["event"] = decode_json(row.pop("event_json"))
        row["raw_event_captured"] = row["event"] is not None

    task = {
        "started_at": rows[0]["ts_iso"],
        "finished_at": rows[-1]["ts_iso"],
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


def dashboard(con: sqlite3.Connection, model: str = "", range_key: str = "", bucket: str = "day"):
    return {
        "state": data_state(con),
        "summary": summary(con, range_key),
        "daily": daily(con, range_key, bucket),
        "turns": turns(con, 150, model, range_key),
        "tasks": tasks(con, 150, range_key),
        "models": models(con, range_key),
    }
