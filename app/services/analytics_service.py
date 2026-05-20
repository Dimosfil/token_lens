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


def summary(range_key: str = ""):
    return with_analytics_db(lambda con: queries.summary(con, range_key))


def data_state():
    state = with_analytics_db(queries.data_state)
    state["import_status"] = import_status()
    return state


def daily(range_key: str = "", bucket: str = "day"):
    return with_analytics_db(lambda con: queries.daily(con, range_key, bucket))


def turns(limit: int, model: str = "", range_key: str = ""):
    return with_analytics_db(lambda con: queries.turns(con, limit, model, range_key))


def tasks(limit: int, range_key: str = ""):
    return with_analytics_db(lambda con: queries.tasks(con, limit, range_key))


def models(range_key: str = ""):
    return with_analytics_db(lambda con: queries.models(con, range_key))


def dashboard(model: str = "", range_key: str = "", bucket: str = "day"):
    payload = with_analytics_db(lambda con: queries.dashboard(con, model, range_key, bucket))
    payload["state"]["import_status"] = import_status()
    payload["import_status"] = payload["state"]["import_status"]
    return payload


def background_import_status():
    return import_status()
