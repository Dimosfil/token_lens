from __future__ import annotations

from collections.abc import Callable

from app.core.config import load_config
from app.storage.connection import connect
from app.storage import queries
from app.storage.schema import init_db


def with_analytics_db(callback: Callable):
    config = load_config()
    init_db(config["analytics_db"])
    with connect(config["analytics_db"]) as con:
        return callback(con)


def summary():
    return with_analytics_db(queries.summary)


def data_state():
    return with_analytics_db(queries.data_state)


def daily():
    return with_analytics_db(queries.daily)


def turns(limit: int, model: str = ""):
    return with_analytics_db(lambda con: queries.turns(con, limit, model))


def tasks(limit: int):
    return with_analytics_db(lambda con: queries.tasks(con, limit))


def models():
    return with_analytics_db(queries.models)


def dashboard(model: str = ""):
    return with_analytics_db(lambda con: queries.dashboard(con, model))
