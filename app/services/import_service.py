from __future__ import annotations

import json

from app.core.config import load_config
from app.core.types import ImportStats
from app.sources.base import UsageSource
from app.sources.codex.adapter import CodexUsageSource
from app.sources.codex.parser import parse_response_event, parse_usage_row
from app.storage.connection import connect
from app.storage.repositories import insert_raw_log, latest_raw_log_id, set_latest_raw_log_id, upsert_turn
from app.storage.schema import init_db


def archive_raw_logs(source: UsageSource, target) -> int:
    iter_rows_after = getattr(source, "iter_rows_after", None)
    if not iter_rows_after:
        return 0

    archived = 0
    last_id = latest_raw_log_id(target)
    if last_id == 0:
        latest_source_id = getattr(source, "latest_log_id", lambda: 0)()
        if latest_source_id:
            set_latest_raw_log_id(target, latest_source_id)
            return 0

    for item in iter_rows_after(last_id):
        if insert_raw_log(target, item):
            archived += 1
    return archived


def import_usage_source(source: UsageSource, analytics_db: str, prices: dict) -> ImportStats:
    init_db(analytics_db)
    thread_names = source.load_thread_names()
    stats = ImportStats()

    target = connect(analytics_db)
    try:
        stats.archived = archive_raw_logs(source, target)
        for item in source.iter_rows():
            stats.scanned += 1
            body = item["feedback_log_body"] or ""
            parsed = parse_response_event(
                item["id"],
                item["ts"],
                item["thread_id"],
                body,
                thread_names,
                prices,
            ) or parse_usage_row(item["id"], item["ts"], item["thread_id"], body, thread_names, prices)
            if not parsed:
                stats.skipped += 1
                continue
            upsert_turn(target, parsed)
            stats.imported += 1
        target.commit()
    finally:
        target.close()

    return stats


def import_codex_logs() -> ImportStats:
    config = load_config()
    source = CodexUsageSource(config["codex_logs_db"], config["codex_session_index"])
    prices = config.get("model_prices_per_million", {})
    return import_usage_source(source, config["analytics_db"], prices)


def main() -> None:
    result = import_codex_logs()
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
