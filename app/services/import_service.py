from __future__ import annotations

import json

from app.core.config import load_config
from app.core.types import ImportStats
from app.sources.codex.parser import parse_response_event, parse_usage_row
from app.sources.codex.reader import iter_usage_log_rows
from app.sources.codex.thread_names import load_thread_names
from app.storage.connection import connect
from app.storage.repositories import upsert_turn
from app.storage.schema import init_db


def import_codex_logs() -> ImportStats:
    config = load_config()
    init_db(config["analytics_db"])
    thread_names = load_thread_names(config["codex_session_index"])
    prices = config.get("model_prices_per_million", {})
    stats = ImportStats()

    with connect(config["analytics_db"]) as target:
        for item in iter_usage_log_rows(config["codex_logs_db"]):
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

    return stats


def main() -> None:
    result = import_codex_logs()
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
