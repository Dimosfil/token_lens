from __future__ import annotations

import json
import os
import logging

from app.core.config import load_config, validate_codex_source_config
from app.core.types import ImportStats
from app.sources.base import UsageSource
from app.sources.codex.adapter import CodexUsageSource
from app.sources.codex.parser import MODEL_RE, first_match, parse_response_event, parse_usage_row
from app.sources.opencode.parser import parse_opencode_db_message, parse_opencode_jsonl_record
from app.sources.opencode.reader import iter_messages_after, jsonl_file_size, max_message_rowid, read_jsonl_after
from app.storage.connection import connect
from app.storage.repositories import (
    get_opencode_import_state,
    backfill_raw_log_display_fields,
    insert_raw_log,
    latest_raw_log_id,
    latest_turn_source_log_id,
    set_latest_raw_log_id,
    set_opencode_import_state,
    upsert_turn,
)
from app.storage.schema import init_db


LOGGER = logging.getLogger("token_lens.import")
OPENCODE_DB_ROWID_LOOKBACK = 100


def archive_raw_logs(source: UsageSource, target, thread_names: dict[str, str] | None = None) -> int:
    iter_rows_after = getattr(source, "iter_rows_after", None)
    if not iter_rows_after:
        return 0

    archived = 0
    thread_names = thread_names or {}
    last_id = latest_raw_log_id(target)
    if last_id == 0:
        latest_source_id = getattr(source, "latest_log_id", lambda: 0)()
        if latest_source_id:
            set_latest_raw_log_id(target, latest_source_id)
            return 0

    for item in iter_rows_after(last_id):
        row = dict(item)
        thread_id = row.get("thread_id")
        body = row.get("feedback_log_body") or ""
        row["thread_name"] = thread_names.get(thread_id)
        row["model"] = first_match(MODEL_RE, body)
        if insert_raw_log(target, row):
            archived += 1
    return archived


def import_usage_source(source: UsageSource, analytics_db: str, prices: dict) -> ImportStats:
    init_db(analytics_db)
    thread_names = source.load_thread_names()
    stats = ImportStats()

    target = connect(analytics_db)
    try:
        stats.archived = archive_raw_logs(source, target, thread_names)
        backfill_raw_log_display_fields(target, thread_names)
        iter_rows = source.iter_rows
        iter_rows_after = getattr(source, "iter_rows_after", None)
        if iter_rows_after:
            last_turn_id = latest_turn_source_log_id(target, "codex")
            iter_rows = lambda: iter_rows_after(last_turn_id)
        for item in iter_rows():
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
    issues = validate_codex_source_config(config)
    if issues:
        LOGGER.warning(
            "codex import skipped because local source config is incomplete: %s",
            "; ".join(issues),
        )
        return ImportStats()
    source = CodexUsageSource(config["codex_logs_db"], config["codex_session_index"])
    prices = config.get("model_prices_per_million", {})
    return import_usage_source(source, config["analytics_db"], prices)


def import_opencode_sources() -> ImportStats:
    config = load_config()
    analytics_db = config["analytics_db"]
    prices = config.get("model_prices_per_million", {})
    stats = ImportStats()

    opencode_db = config.get("opencode_db", "")
    jsonl_path = config.get("opencode_tokens_jsonl", "")
    db_exists = bool(opencode_db) and os.path.isfile(opencode_db)
    jsonl_exists = bool(jsonl_path) and os.path.isfile(jsonl_path)
    if not db_exists and not jsonl_exists:
        return stats

    init_db(analytics_db)
    target = connect(analytics_db)
    try:
        state = get_opencode_import_state(target)
        last_rowid = state["last_rowid"]
        last_jsonl_offset = state["last_jsonl_offset"]
        last_jsonl_size = state["last_jsonl_size"]

        if db_exists:
            if max_message_rowid(opencode_db) < last_rowid:
                last_rowid = 0
            scan_after_rowid = max(last_rowid - OPENCODE_DB_ROWID_LOOKBACK, 0)
            max_rowid = last_rowid
            for msg in iter_messages_after(opencode_db, scan_after_rowid):
                stats.scanned += 1
                row = parse_opencode_db_message(msg, prices)
                if not row:
                    stats.skipped += 1
                    continue
                upsert_turn(target, row)
                stats.imported += 1
                max_rowid = msg["_rowid"]
            last_rowid = max_rowid

        if jsonl_exists:
            current_size = jsonl_file_size(jsonl_path)
            if current_size < last_jsonl_offset:
                last_jsonl_offset = 0
            new_offset = last_jsonl_offset
            for record, offset in read_jsonl_after(jsonl_path, last_jsonl_offset):
                new_offset = offset
                stats.scanned += 1
                row = parse_opencode_jsonl_record(record, prices)
                if not row:
                    stats.skipped += 1
                    continue
                upsert_turn(target, row)
                stats.imported += 1
            last_jsonl_offset = new_offset
            last_jsonl_size = current_size

        set_opencode_import_state(target, last_rowid, last_jsonl_offset, last_jsonl_size)
        target.commit()
    finally:
        target.close()

    return stats


def main() -> None:
    result = import_codex_logs()
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
