from __future__ import annotations

from collections.abc import Callable

from app.core.config import load_config
from app.services.background import import_status
from app.storage.connection import connect
from app.storage import queries
from app.storage.schema import init_db


def with_analytics_db(callback: Callable):
    config = load_config()
    init_db(config["analytics_db"])
    con = connect(config["analytics_db"])
    try:
        return callback(con)
    finally:
        con.close()


def summary(range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.summary(con, range_key, start_ts, end_ts, source))


def data_state():
    state = with_analytics_db(queries.data_state)
    state["import_status"] = import_status()
    return state


def daily(range_key: str = "", bucket: str = "day", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.daily(con, range_key, bucket, start_ts, end_ts, source))


def turns(limit: int, model: str = "", range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.turns(con, limit, model, range_key, start_ts, end_ts, source))


def tasks(limit: int, range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.tasks(con, limit, range_key, start_ts, end_ts, source))


def bucket_tasks(period: str, bucket: str = "day", range_key: str = "", start_ts: int | None = None, end_ts: int | None = None, source: str = ""):
    return with_analytics_db(lambda con: queries.bucket_tasks(con, period, bucket, range_key, start_ts, end_ts, source))


def task_detail(thread_id: str, turn_id: str):
    return with_analytics_db(lambda con: queries.task_detail(con, thread_id, turn_id))


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
):
    payload = with_analytics_db(lambda con: queries.dashboard(con, model, range_key, bucket, task_mode, start_ts, end_ts, source))
    payload["state"]["import_status"] = import_status()
    payload["import_status"] = payload["state"]["import_status"]
    return payload


def background_import_status():
    return import_status()
