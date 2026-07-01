from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3
import time

from app.sources.codex.parser import parse_response_create_request
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


RAW_ONLY_TASK_SCAN_LIMIT = 10000
TASK_USAGE_SCAN_MULTIPLIER = 4


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


def _usage_clause(where: str) -> str:
    return _and_clause(
        where,
        """
        not (
          source = 'codex'
          and (
            total_tokens <= 0
            or total_tokens < input_tokens + output_tokens
            or (
              input_tokens = 0
              and cached_input_tokens = 0
              and output_tokens = 0
              and reasoning_output_tokens = 0
            )
          )
        )
        """,
    )


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


def _expected_periods(
    range_key: str,
    bucket: str,
    time_mode: str = TIME_MODE_LOCAL,
    start_ts: int | None = None,
    end_ts: int | None = None,
) -> list[str]:
    tz = timezone.utc if normalize_time_mode(time_mode) == "utc" else None
    if normalize_range(range_key) == CUSTOM_RANGE:
        if start_ts is None or end_ts is None:
            return []
        lower, upper = sorted((int(start_ts), int(end_ts)))
        start = datetime.fromtimestamp(lower, tz)
        end = datetime.fromtimestamp(upper, tz)
        periods = []
        if bucket == "hour":
            cursor = start.replace(minute=0, second=0, microsecond=0)
            last = end.replace(minute=0, second=0, microsecond=0)
            while cursor <= last:
                periods.append(cursor.strftime("%Y-%m-%d %H:00"))
                cursor += timedelta(hours=1)
            return periods
        if bucket == "day":
            cursor = start.replace(hour=0, minute=0, second=0, microsecond=0)
            last = end.replace(hour=0, minute=0, second=0, microsecond=0)
            while cursor <= last:
                periods.append(cursor.date().isoformat())
                cursor += timedelta(days=1)
            return periods
        if bucket == "month":
            cursor = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            while cursor <= last:
                periods.append(cursor.strftime("%Y-%m"))
                cursor = _shift_month(cursor, 1)
            return periods
        return []

    count = MAX_BUCKETS.get((normalize_range(range_key), bucket))
    if not count:
        return []

    now = time.time()
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


def _fill_bucket_rows(
    rows: list[dict],
    range_key: str,
    bucket: str,
    time_mode: str = TIME_MODE_LOCAL,
    start_ts: int | None = None,
    end_ts: int | None = None,
) -> list[dict]:
    periods = _expected_periods(range_key, bucket, time_mode, start_ts, end_ts)
    if not periods:
        return _trim_bucket_rows(rows, range_key, bucket)

    by_period = {row["period"]: row for row in rows}
    return [by_period.get(period, _empty_bucket_row(period, bucket)) for period in periods]


def summary(con: sqlite3.Connection, range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    if source == "opencode":
        return opencode_summary(con, range_key, start_ts, end_ts)
    if source == "codex":
        return codex_summary(con, range_key, start_ts, end_ts)

    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
    where = _usage_clause(where)
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


def codex_summary(
    con: sqlite3.Connection,
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
):
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, "codex")
    where = _usage_clause(where)
    cte = f"""
        with aggregates as (
            select thread_id,
                   max(thread_name) as thread_name,
                   max(ts_iso) as latest_turn,
                   group_concat(distinct model) as models,
                   group_concat(distinct status) as statuses,
                   count(*) as model_calls,
                   sum(input_tokens) as input_tokens,
                   sum(cached_input_tokens) as cached_input_tokens,
                   sum(output_tokens) as output_tokens,
                   sum(reasoning_output_tokens) as reasoning_output_tokens,
                   sum(total_tokens) as log_total_tokens,
                   sum(estimated_cost) as estimated_cost
            from turns
            {where}
            group by thread_id
        ),
        adjusted as (
            select aggregates.*,
                   coalesce(nullif(codex_threads.thread_name, ''), aggregates.thread_name) as display_thread_name,
                   codex_threads.tokens_used as state_tokens_used
            from aggregates
            left join codex_threads on codex_threads.thread_id = aggregates.thread_id
        )
    """
    row = con.execute(
        cte
        + """
        select coalesce(sum(model_calls), 0) as turns,
               count(*) as threads,
               coalesce(sum(input_tokens), 0) as input_tokens,
               coalesce(sum(output_tokens), 0) as output_tokens,
               coalesce(sum(cached_input_tokens), 0) as cached_input_tokens,
               coalesce(sum(reasoning_output_tokens), 0) as reasoning_output_tokens,
               coalesce(sum(log_total_tokens), 0) as total_tokens,
               coalesce(sum(estimated_cost), 0) as estimated_cost,
               max(latest_turn) as latest_turn
        from adjusted
        """,
        params,
    ).fetchone()
    top = con.execute(
        cte
        + """
        select 'codex' as source,
               latest_turn as ts_iso,
               thread_id,
               display_thread_name as thread_name,
               'chat:' || thread_id as turn_id,
               null as response_id,
               statuses as status,
               models as model,
               log_total_tokens as total_tokens,
               input_tokens,
               output_tokens,
               reasoning_output_tokens,
               state_tokens_used,
               log_total_tokens
        from adjusted
        order by log_total_tokens desc
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
    where = _usage_clause(where)
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
    return _fill_bucket_rows(rows, range_key, normalized_bucket, time_mode, start_ts, end_ts)


def turns(con: sqlite3.Connection, limit: int, model: str = "", range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    params = []
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
    where = _usage_clause(where)
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
    return codex_tasks(con, limit, range_key, start_ts, end_ts)


def codex_tasks(
    con: sqlite3.Connection,
    limit: int | None,
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
):
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, "codex")
    where = _usage_clause(where)
    limit_clause = ""
    usage_params = list(params)
    if limit is not None:
        limit_clause = "limit ?"
        usage_params.append(max(limit * TASK_USAGE_SCAN_MULTIPLIER, limit + 20))

    usage_rows = rows_to_dicts(con.execute(
        f"""
        with aggregates as (
            select min(ts_iso) as started_at,
                   max(ts_iso) as finished_at,
                   max(ts) - min(ts) as elapsed_seconds,
                   min(source_log_id) as first_source_log_id,
                   max(source_log_id) as last_source_log_id,
                   thread_id,
                   max(thread_name) as thread_name,
                   group_concat(distinct turn_id) as turn_ids,
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
                   sum(total_tokens) as log_total_tokens,
                   sum(estimated_cost) as estimated_cost,
                   max(ts) as latest_ts
            from turns
            {where}
            group by thread_id
            order by max(ts) desc
            {limit_clause}
        )
        select aggregates.started_at,
               aggregates.finished_at,
               aggregates.elapsed_seconds,
               'codex' as source,
               aggregates.first_source_log_id,
               aggregates.last_source_log_id,
               aggregates.thread_id,
               coalesce(nullif(codex_threads.thread_name, ''), aggregates.thread_name) as thread_name,
               'chat:' || aggregates.thread_id as turn_id,
               aggregates.turn_ids,
               aggregates.submission_ids,
               aggregates.response_ids,
               coalesce(nullif(aggregates.models, ''), codex_threads.model) as models,
               aggregates.statuses,
               coalesce(nullif(aggregates.efforts, ''), codex_threads.reasoning_effort) as efforts,
               1 as has_usage,
               aggregates.model_calls,
               0 as raw_event_calls,
               aggregates.input_tokens,
               aggregates.cached_input_tokens,
               aggregates.non_cached_input_tokens,
               aggregates.output_tokens,
               aggregates.reasoning_output_tokens,
               aggregates.log_total_tokens as total_tokens,
               cast(round(aggregates.log_total_tokens * 1.0 / aggregates.model_calls, 0) as integer) as total_tokens_per_call,
               aggregates.estimated_cost,
               codex_threads.tokens_used as state_tokens_used,
               aggregates.log_total_tokens
        from aggregates
        left join codex_threads on codex_threads.thread_id = aggregates.thread_id
        order by aggregates.latest_ts desc
        """,
        usage_params,
    ).fetchall())

    rows = usage_rows + raw_only_tasks(con, range_key, start_ts, end_ts)
    rows.sort(key=lambda row: (row.get("finished_at") or "", row.get("last_source_log_id") or 0), reverse=True)
    return rows[:limit] if limit is not None else rows



def raw_only_tasks(
    con: sqlite3.Connection,
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
):
    where, params = _range_clause(range_key, start_ts, end_ts)
    where = _and_clause(
        where,
        "thread_name is not null",
    )
    where = _and_clause(
        where,
        """
        not exists (
          select 1
          from turns
          where turns.source = 'codex'
            and turns.thread_id = recent_raw.thread_id
        )
        """,
    )
    params = [RAW_ONLY_TASK_SCAN_LIMIT, *params]
    return rows_to_dicts(con.execute(
        f"""
        with recent_raw as (
            select source_log_id, ts, ts_iso, thread_id, thread_name, model
            from raw_logs
            where thread_id is not null
            order by source_log_id desc
            limit ?
        )
        select min(ts_iso) as started_at,
               max(ts_iso) as finished_at,
               max(ts) - min(ts) as elapsed_seconds,
               'codex' as source,
               min(source_log_id) as first_source_log_id,
               max(source_log_id) as last_source_log_id,
               thread_id,
               max(thread_name) as thread_name,
               'raw:' || thread_id as turn_id,
               null as submission_ids,
               null as response_ids,
               group_concat(distinct model) as models,
               'usage-missing' as statuses,
               0 as has_usage,
               0 as model_calls,
               count(*) as raw_event_calls,
               null as input_tokens,
               null as cached_input_tokens,
               null as non_cached_input_tokens,
               null as output_tokens,
               null as reasoning_output_tokens,
               null as total_tokens,
               null as total_tokens_per_call,
               null as estimated_cost
        from recent_raw
        {where}
        group by thread_id
        order by max(ts) desc
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
                   group_concat(distinct turn_id) as turn_ids,
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
                   sum(estimated_cost) as estimated_cost
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
               'chat:' || aggregates.thread_id as turn_id,
               aggregates.turn_ids,
               aggregates.submission_ids,
               aggregates.response_ids,
               aggregates.models,
               aggregates.statuses,
               aggregates.efforts,
               1 as has_usage,
               aggregates.model_calls,
               0 as raw_event_calls,
               aggregates.input_tokens,
               aggregates.cached_input_tokens,
               aggregates.non_cached_input_tokens,
               aggregates.output_tokens,
               aggregates.reasoning_output_tokens,
               aggregates.total_tokens,
               cast(round(aggregates.total_tokens * 1.0 / aggregates.model_calls, 0) as integer) as total_tokens_per_call,
               aggregates.estimated_cost
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
    if source == "opencode":
        return opencode_task_buckets(con, range_key, bucket, start_ts, end_ts, time_mode)
    return codex_task_buckets(con, range_key, bucket, start_ts, end_ts, time_mode)


def codex_task_buckets(
    con: sqlite3.Connection,
    range_key: str = "",
    bucket: str = "day",
    start_ts: int | None = None,
    end_ts: int | None = None,
    time_mode: str = TIME_MODE_LOCAL,
):
    normalized_bucket = normalize_bucket(bucket, range_key)
    period_expr = _bucket_expr(normalized_bucket, time_mode)
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, "codex")
    where = _usage_clause(where)
    return rows_to_dicts(con.execute(
        f"""
        with scoped as (
            select {period_expr} as period, *
            from turns
            {where}
        ),
        thread_periods as (
            select period,
                   min(ts_iso) as started_at,
                   max(ts_iso) as finished_at,
                   max(ts) - min(ts) as elapsed_seconds,
                   min(ts) as bucket_start_ts,
                   max(ts) as bucket_end_ts,
                   thread_id,
                   count(*) as model_calls,
                   group_concat(distinct model) as models,
                   group_concat(distinct status) as statuses,
                   group_concat(distinct reasoning_effort) as efforts,
                   sum(input_tokens) as input_tokens,
                   sum(cached_input_tokens) as cached_input_tokens,
                   sum(non_cached_input_tokens) as non_cached_input_tokens,
                   sum(output_tokens) as output_tokens,
                   sum(reasoning_output_tokens) as reasoning_output_tokens,
                   sum(total_tokens) as period_log_total_tokens,
                   sum(estimated_cost) as estimated_cost
            from scoped
            group by period, thread_id
        )
        select period,
               min(started_at) as started_at,
               max(finished_at) as finished_at,
               max(bucket_end_ts) - min(bucket_start_ts) as elapsed_seconds,
               min(bucket_start_ts) as bucket_start_ts,
               max(bucket_end_ts) as bucket_end_ts,
               count(distinct thread_id) as tasks,
               sum(model_calls) as model_calls,
               group_concat(distinct models) as models,
               group_concat(distinct statuses) as statuses,
               group_concat(distinct efforts) as efforts,
               sum(input_tokens) as input_tokens,
               sum(cached_input_tokens) as cached_input_tokens,
               sum(non_cached_input_tokens) as non_cached_input_tokens,
               sum(output_tokens) as output_tokens,
               sum(reasoning_output_tokens) as reasoning_output_tokens,
               sum(period_log_total_tokens) as total_tokens,
               cast(round(sum(period_log_total_tokens) * 1.0 / sum(model_calls), 0) as integer) as total_tokens_per_call,
               sum(estimated_cost) as estimated_cost
        from thread_periods
        group by period
        order by period desc
        """,
        params,
    ).fetchall())


def opencode_task_buckets(
    con: sqlite3.Connection,
    range_key: str = "",
    bucket: str = "day",
    start_ts: int | None = None,
    end_ts: int | None = None,
    time_mode: str = TIME_MODE_LOCAL,
):
    normalized_bucket = normalize_bucket(bucket, range_key)
    period_expr = _bucket_expr(normalized_bucket, time_mode)
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, "opencode")
    return rows_to_dicts(con.execute(
        f"""
        select {period_expr} as period,
               min(ts_iso) as started_at,
               max(ts_iso) as finished_at,
               max(ts) - min(ts) as elapsed_seconds,
               min(ts) as bucket_start_ts,
               max(ts) as bucket_end_ts,
               count(distinct thread_id) as tasks,
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
    if source == "opencode":
        return opencode_bucket_tasks(con, period, bucket, range_key, start_ts, end_ts, time_mode)
    return codex_bucket_tasks(con, period, bucket, range_key, start_ts, end_ts, time_mode)


def codex_bucket_tasks(
    con: sqlite3.Connection,
    period: str,
    bucket: str = "day",
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
    time_mode: str = TIME_MODE_LOCAL,
):
    normalized_bucket = normalize_bucket(bucket, range_key)
    period_expr = _bucket_expr(normalized_bucket, time_mode)
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, "codex")
    where = _usage_clause(where)
    query_params = list(params)
    query_params.append(period)
    return rows_to_dicts(con.execute(
        f"""
        with scoped as (
            select {period_expr} as period, *
            from turns
            {where}
        ),
        aggregates as (
            select min(ts_iso) as started_at,
                   max(ts_iso) as finished_at,
                   max(ts) - min(ts) as elapsed_seconds,
                   min(source_log_id) as first_source_log_id,
                   max(source_log_id) as last_source_log_id,
                   thread_id,
                   max(thread_name) as thread_name,
                   group_concat(distinct turn_id) as turn_ids,
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
                   sum(total_tokens) as period_log_total_tokens,
                   sum(estimated_cost) as estimated_cost,
                   max(ts) as latest_ts,
                   period
            from scoped
            group by period, thread_id
        ),
        adjusted as (
            select aggregates.*,
                   codex_threads.tokens_used as state_tokens_used
            from aggregates
            left join codex_threads on codex_threads.thread_id = aggregates.thread_id
        )
        select adjusted.started_at,
               adjusted.finished_at,
               adjusted.elapsed_seconds,
               adjusted.first_source_log_id,
               adjusted.last_source_log_id,
               adjusted.thread_id,
               coalesce(nullif(codex_threads.thread_name, ''), adjusted.thread_name) as thread_name,
               'chat:' || adjusted.thread_id as turn_id,
               adjusted.turn_ids,
               adjusted.submission_ids,
               adjusted.response_ids,
               coalesce(nullif(adjusted.models, ''), codex_threads.model) as models,
               adjusted.statuses,
               coalesce(nullif(adjusted.efforts, ''), codex_threads.reasoning_effort) as efforts,
               adjusted.model_calls,
               adjusted.input_tokens,
               adjusted.cached_input_tokens,
               adjusted.non_cached_input_tokens,
               adjusted.output_tokens,
               adjusted.reasoning_output_tokens,
               adjusted.period_log_total_tokens as total_tokens,
               cast(round(adjusted.period_log_total_tokens * 1.0 / adjusted.model_calls, 0) as integer) as total_tokens_per_call,
               adjusted.estimated_cost,
               adjusted.state_tokens_used,
               adjusted.period_log_total_tokens as log_total_tokens
        from adjusted
        left join codex_threads on codex_threads.thread_id = adjusted.thread_id
        where adjusted.period = ?
        order by adjusted.latest_ts desc
        """,
        query_params,
    ).fetchall())


def opencode_bucket_tasks(
    con: sqlite3.Connection,
    period: str,
    bucket: str = "day",
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
    time_mode: str = TIME_MODE_LOCAL,
):
    normalized_bucket = normalize_bucket(bucket, range_key)
    period_expr = _bucket_expr(normalized_bucket, time_mode)
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, "opencode")
    where = _and_clause(where, f"{period_expr} = ?")
    params.append(period)
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
                   group_concat(distinct turn_id) as turn_ids,
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
                   sum(estimated_cost) as estimated_cost
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
               'chat:' || aggregates.thread_id as turn_id,
               aggregates.turn_ids,
               aggregates.submission_ids,
               aggregates.response_ids,
               aggregates.models,
               aggregates.statuses,
               aggregates.efforts,
               1 as has_usage,
               aggregates.model_calls,
               0 as raw_event_calls,
               aggregates.input_tokens,
               aggregates.cached_input_tokens,
               aggregates.non_cached_input_tokens,
               aggregates.output_tokens,
               aggregates.reasoning_output_tokens,
               aggregates.total_tokens,
               cast(round(aggregates.total_tokens * 1.0 / aggregates.model_calls, 0) as integer) as total_tokens_per_call,
               aggregates.estimated_cost
        from aggregates
        join ranked on ranked.thread_id = aggregates.thread_id and ranked.row_rank = 1
        order by ranked.ts desc
        """,
        params,
    ).fetchall())


def task_detail(con: sqlite3.Connection, thread_id: str, turn_id: str):
    if str(turn_id or "").startswith("chat:"):
        rows = rows_to_dicts(con.execute(
            """
            select source, source_log_id, ts, ts_iso, day, thread_id, thread_name, turn_id, response_id,
                   submission_id, status, model, reasoning_effort, input_tokens,
                   cached_input_tokens, non_cached_input_tokens, output_tokens,
                   reasoning_output_tokens, total_tokens, estimated_cost,
                   request_json, response_json, event_json
            from turns
            where thread_id = ?
            order by ts, source_log_id
            """,
            [thread_id],
        ).fetchall())
    else:
        rows = rows_to_dicts(con.execute(
            """
            select source, source_log_id, ts, ts_iso, day, thread_id, thread_name, turn_id, response_id,
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
        if row["request"] is None and row.get("source") == "codex":
            row["request"] = _request_payload_from_raw_logs(con, row)
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
    state_row = con.execute(
        """
        select thread_name, tokens_used, model, reasoning_effort
        from codex_threads
        where thread_id = ?
        """,
        [thread_id],
    ).fetchone()
    if state_row:
        if state_row["thread_name"]:
            task["thread_name"] = state_row["thread_name"]
        state_tokens = int(state_row["tokens_used"] or 0)
        if state_tokens:
            task["state_tokens_used"] = state_tokens
            task["log_total_tokens"] = task["total_tokens"]
        if state_row["model"]:
            task["models"] = sorted(set(task["models"]) | {state_row["model"]})
        if state_row["reasoning_effort"]:
            task["efforts"] = sorted(
                set(row["reasoning_effort"] for row in rows if row["reasoning_effort"])
                | {state_row["reasoning_effort"]}
            )
    task["raw_event_captured"] = task["raw_event_calls"] == task["model_calls"]
    task["total_tokens_per_call"] = round(task["total_tokens"] / task["model_calls"]) if task["model_calls"] else 0
    return {"task": task, "calls": rows}


def _request_payload_from_raw_logs(con: sqlite3.Connection, row: dict):
    candidates = con.execute(
        """
        select source_log_id, ts, feedback_log_body
        from raw_logs
        where thread_id = ?
          and feedback_log_body like ?
          and (
            feedback_log_body like '%websocket request: {"type":"response.create"%'
            or feedback_log_body like '%websocket request: {"type": "response.create"%'
          )
        order by source_log_id desc
        limit 10
        """,
        [row["thread_id"], f"%turn.id={row['turn_id']}%"],
    ).fetchall()
    for candidate in candidates:
        payload = parse_response_create_request(
            candidate["source_log_id"],
            candidate["ts"],
            row["thread_id"],
            candidate["feedback_log_body"] or "",
        )
        if payload and payload.get("model") == row.get("model"):
            return decode_json(payload.get("request_json"))
    return None


def models(con: sqlite3.Connection, range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    where, params = _range_clause(range_key, start_ts, end_ts)
    where, params = _source_clause(where, params, source)
    where = _usage_clause(where)
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
        where not (
          source = 'codex'
          and (
            total_tokens <= 0
            or total_tokens < input_tokens + output_tokens
            or (
              input_tokens = 0
              and cached_input_tokens = 0
              and output_tokens = 0
              and reasoning_output_tokens = 0
            )
          )
        )
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
