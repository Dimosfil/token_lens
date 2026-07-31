from __future__ import annotations

from collections.abc import Callable

from app.core.config import load_config
from app.services.codex_account_service import read_usage_limits
from app.services.data_refresh import import_status, source_warnings
from app.sources.codex.session_transcript import load_turn_payloads
from app.storage.connection import connect
from app.storage import queries
from app.storage.schema import init_db


def with_analytics_db(callback: Callable):
    config = load_config()
    return _with_configured_analytics_db(config, callback)


def summary(range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.summary(con, range_key, start_ts, end_ts, source))


def data_state(include_raw: bool = True):
    config = load_config()
    state = with_analytics_db(lambda con: queries.data_state(con, include_raw=include_raw))
    state["import_status"] = import_status()
    state["source_warnings"] = source_warnings(config)
    return state


def usage_limits():
    return read_usage_limits(load_config())


def daily(
    range_key: str = "",
    bucket: str = "day",
    start_ts: int | None = None,
    end_ts: int | None = None,
    source: str = "",
    time_mode: str = "",
):
    return with_analytics_db(lambda con: queries.daily(con, range_key, bucket, start_ts, end_ts, source, time_mode))


def turns(limit: int, model: str = "", range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.turns(con, limit, model, range_key, start_ts, end_ts, source))


def tasks(limit: int, range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.tasks(con, limit, range_key, start_ts, end_ts, source))


def bucket_tasks(
    period: str,
    bucket: str = "day",
    range_key: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
    source: str = "",
    time_mode: str = "",
):
    return with_analytics_db(lambda con: queries.bucket_tasks(con, period, bucket, range_key, start_ts, end_ts, source, time_mode))


def task_detail(thread_id: str, turn_id: str):
    config = load_config()
    detail = _with_configured_analytics_db(
        config,
        lambda con: queries.task_detail(con, thread_id, turn_id),
    )
    return _add_codex_session_payloads(detail, config.get("codex_session_index", ""), thread_id)


def _with_configured_analytics_db(config: dict, callback: Callable):
    init_db(config["analytics_db"])
    con = connect(config["analytics_db"])
    try:
        return callback(con)
    finally:
        con.close()


def _add_codex_session_payloads(detail: dict, session_path: str, thread_id: str) -> dict:
    calls = detail.get("calls") if isinstance(detail, dict) else None
    if not isinstance(calls, list):
        return detail
    missing_calls = [
        call for call in calls
        if call.get("source") == "codex" and (call.get("request") is None or call.get("response") is None)
    ]
    turn_ids = {call.get("turn_id") for call in missing_calls if call.get("turn_id")}
    payloads = load_turn_payloads(session_path, thread_id, turn_ids)
    for call in missing_calls:
        payload = payloads.get(call.get("turn_id"), {})
        if call.get("request") is None and payload.get("request") is not None:
            call["request"] = payload["request"]
            call["request_source"] = "codex_session_transcript"
        if call.get("response") is None and payload.get("response") is not None:
            call["response"] = payload["response"]
            call["response_source"] = "codex_session_transcript"
    return detail


def models(range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.models(con, range_key, start_ts, end_ts, source))


def dashboard(
    model: str = "",
    range_key: str = "",
    bucket: str = "day",
    task_mode: str = "",
    start_ts: int | None = None,
    end_ts: int | None = None,
    source: str = "",
    time_mode: str = "",
):
    config = load_config()
    payload = with_analytics_db(lambda con: queries.dashboard(
        con,
        model,
        range_key,
        bucket,
        task_mode,
        start_ts,
        end_ts,
        source,
        time_mode,
    ))
    payload["usage_limits"] = read_usage_limits(config)
    payload["state"]["import_status"] = import_status()
    payload["state"]["source_warnings"] = source_warnings(config)
    payload["import_status"] = payload["state"]["import_status"]
    payload["source_warnings"] = payload["state"]["source_warnings"]
    return payload


def background_import_status():
    return import_status()
