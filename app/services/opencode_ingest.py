from __future__ import annotations

from app.core.config import load_config
from app.sources.opencode.parser import parse_opencode_event
from app.storage.connection import connect
from app.storage.repositories import upsert_turn
from app.storage.schema import init_db


def ingest_event(payload: dict) -> dict:
    config = load_config()
    init_db(config["analytics_db"])
    row = parse_opencode_event(payload, config.get("model_prices_per_million", {}))
    if not row:
        return {"imported": 0, "skipped": 1, "reason": "no usage payload"}

    con = connect(config["analytics_db"])
    try:
        upsert_turn(con, row)
        con.commit()
    finally:
        con.close()

    return {
        "imported": 1,
        "skipped": 0,
        "source_log_id": row["source_log_id"],
        "thread_id": row["thread_id"],
        "turn_id": row["turn_id"],
        "model": row["model"],
        "total_tokens": row["total_tokens"],
    }
