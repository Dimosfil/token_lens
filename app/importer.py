from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config
from .db import connect, init_db


TOKEN_RE = re.compile(r"codex\.turn\.token_usage\.([a-z_]+)=([0-9]+)")
MODEL_RE = re.compile(r"(?:^| )model=([^ }]+)")
THREAD_RE = re.compile(r"thread\.id=([^ }]+)")
TURN_RE = re.compile(r"turn\.id=([^ }]+)")
SUBMISSION_RE = re.compile(r"submission\.id=\"?([^\" }]+)")
EFFORT_RE = re.compile(r"codex\.turn\.reasoning_effort=([^ }]+)")
RESPONSE_COMPLETED = '{"type":"response.completed"'


@dataclass
class ImportStats:
    scanned: int = 0
    imported: int = 0
    skipped: int = 0


def load_thread_names(path: str) -> dict[str, str]:
    index_path = Path(path)
    if not index_path.exists():
        return {}

    names: dict[str, str] = {}
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            thread_id = row.get("id")
            thread_name = row.get("thread_name")
            if thread_id and thread_name:
                names[thread_id] = thread_name
    return names


def first_match(pattern: re.Pattern[str], text: str, default: str | None = None) -> str | None:
    match = pattern.search(text)
    return match.group(1) if match else default


def estimate_cost(row: dict, prices: dict) -> float:
    price = prices.get(row["model"], {})
    input_price = float(price.get("input", 0))
    cached_price = float(price.get("cached_input", input_price))
    output_price = float(price.get("output", 0))

    return (
        row["non_cached_input_tokens"] * input_price
        + row["cached_input_tokens"] * cached_price
        + row["output_tokens"] * output_price
    ) / 1_000_000


def parse_usage_row(source_log_id: int, ts: int, thread_id: str | None, body: str, thread_names: dict[str, str], prices: dict) -> dict | None:
    if 'instrument_name="codex.turn.token_usage"' not in body:
        return None

    token_pairs = {name: int(value) for name, value in TOKEN_RE.findall(body)}
    if not token_pairs:
        return None

    resolved_thread_id = thread_id or first_match(THREAD_RE, body)
    turn_id = first_match(TURN_RE, body)
    model = first_match(MODEL_RE, body)
    if not resolved_thread_id or not turn_id or not model:
        return None

    dt = datetime.fromtimestamp(ts, timezone.utc)
    row = {
        "source_log_id": source_log_id,
        "response_id": None,
        "ts": ts,
        "ts_iso": dt.isoformat(),
        "day": dt.date().isoformat(),
        "thread_id": resolved_thread_id,
        "thread_name": thread_names.get(resolved_thread_id),
        "turn_id": turn_id,
        "submission_id": first_match(SUBMISSION_RE, body),
        "model": model,
        "reasoning_effort": first_match(EFFORT_RE, body),
        "input_tokens": token_pairs.get("input_tokens", 0),
        "cached_input_tokens": token_pairs.get("cached_input_tokens", 0),
        "non_cached_input_tokens": token_pairs.get("non_cached_input_tokens", 0),
        "output_tokens": token_pairs.get("output_tokens", 0),
        "reasoning_output_tokens": token_pairs.get("reasoning_output_tokens", 0),
        "total_tokens": token_pairs.get("total_tokens", 0),
    }
    row["estimated_cost"] = estimate_cost(row, prices)
    row["imported_at"] = datetime.now(timezone.utc).isoformat()
    return row


def parse_response_completed(source_log_id: int, ts: int, thread_id: str | None, body: str, thread_names: dict[str, str], prices: dict) -> dict | None:
    idx = body.find(RESPONSE_COMPLETED)
    if idx < 0:
        return None

    try:
        event, _ = json.JSONDecoder().raw_decode(body[idx:])
    except json.JSONDecodeError:
        return None

    response = event.get("response") or {}
    usage = response.get("usage") or {}
    if not usage:
        return None

    resolved_thread_id = thread_id or first_match(THREAD_RE, body)
    turn_id = first_match(TURN_RE, body) or response.get("id")
    model = response.get("model") or first_match(MODEL_RE, body)
    if not resolved_thread_id or not turn_id or not model:
        return None

    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    cached_tokens = int(input_details.get("cached_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    reasoning_tokens = int(output_details.get("reasoning_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))

    dt = datetime.fromtimestamp(ts, timezone.utc)
    row = {
        "source_log_id": source_log_id,
        "response_id": response.get("id"),
        "ts": ts,
        "ts_iso": dt.isoformat(),
        "day": dt.date().isoformat(),
        "thread_id": resolved_thread_id,
        "thread_name": thread_names.get(resolved_thread_id),
        "turn_id": turn_id,
        "submission_id": first_match(SUBMISSION_RE, body),
        "model": model,
        "reasoning_effort": first_match(EFFORT_RE, body),
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "non_cached_input_tokens": max(input_tokens - cached_tokens, 0),
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
    }
    row["estimated_cost"] = estimate_cost(row, prices)
    row["imported_at"] = datetime.now(timezone.utc).isoformat()
    return row


def import_codex_logs() -> ImportStats:
    config = load_config()
    init_db(config["analytics_db"])
    thread_names = load_thread_names(config["codex_session_index"])
    prices = config.get("model_prices_per_million", {})
    stats = ImportStats()

    source_path = config["codex_logs_db"]
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row

    with connect(config["analytics_db"]) as target:
        rows = source.execute(
            """
            select id, ts, thread_id, feedback_log_body
            from logs
            where (
              feedback_log_body like '%codex.turn.token_usage%'
              and feedback_log_body like '%instrument_name="codex.turn.token_usage"%'
            ) or (
              feedback_log_body like '%"type":"response.completed"%'
              and feedback_log_body like '%"usage"%'
            )
            order by id
            """
        )

        for item in rows:
            stats.scanned += 1
            body = item["feedback_log_body"] or ""
            parsed = parse_response_completed(
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
            target.execute(
                """
                insert or replace into turns (
                  source_log_id, response_id, ts, ts_iso, day, thread_id, thread_name, turn_id,
                  submission_id, model, reasoning_effort, input_tokens,
                  cached_input_tokens, non_cached_input_tokens, output_tokens,
                  reasoning_output_tokens, total_tokens, estimated_cost, imported_at
                ) values (
                  :source_log_id, :response_id, :ts, :ts_iso, :day, :thread_id, :thread_name, :turn_id,
                  :submission_id, :model, :reasoning_effort, :input_tokens,
                  :cached_input_tokens, :non_cached_input_tokens, :output_tokens,
                  :reasoning_output_tokens, :total_tokens, :estimated_cost, :imported_at
                )
                on conflict(response_id) do update set
                  source_log_id = excluded.source_log_id,
                  ts = excluded.ts,
                  ts_iso = excluded.ts_iso,
                  day = excluded.day,
                  thread_id = excluded.thread_id,
                  thread_name = excluded.thread_name,
                  turn_id = excluded.turn_id,
                  submission_id = excluded.submission_id,
                  model = excluded.model,
                  reasoning_effort = excluded.reasoning_effort,
                  input_tokens = excluded.input_tokens,
                  cached_input_tokens = excluded.cached_input_tokens,
                  non_cached_input_tokens = excluded.non_cached_input_tokens,
                  output_tokens = excluded.output_tokens,
                  reasoning_output_tokens = excluded.reasoning_output_tokens,
                  total_tokens = excluded.total_tokens,
                  estimated_cost = excluded.estimated_cost,
                  imported_at = excluded.imported_at
                """,
                parsed,
            )
            stats.imported += 1
        target.commit()

    source.close()
    return stats


if __name__ == "__main__":
    result = import_codex_logs()
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
