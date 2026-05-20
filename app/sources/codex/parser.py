from __future__ import annotations

import json
import re
from datetime import datetime, timezone


TOKEN_RE = re.compile(r"codex\.turn\.token_usage\.([a-z_]+)=([0-9]+)")
MODEL_RE = re.compile(r"(?:^| )model=([^ }]+)")
THREAD_RE = re.compile(r"thread\.id=([^ }]+)")
TURN_RE = re.compile(r"turn\.id=([^ }]+)")
SUBMISSION_RE = re.compile(r"submission\.id=\"?([^\" }]+)")
EFFORT_RE = re.compile(r"codex\.turn\.reasoning_effort=([^ }]+)")
RESPONSE_EVENT_RE = re.compile(r'\{"type":"response\.(created|in_progress|completed)"')


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


def parse_usage_row(
    source_log_id: int,
    ts: int,
    thread_id: str | None,
    body: str,
    thread_names: dict[str, str],
    prices: dict,
) -> dict | None:
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
        "status": "completed",
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


def parse_response_event(
    source_log_id: int,
    ts: int,
    thread_id: str | None,
    body: str,
    thread_names: dict[str, str],
    prices: dict,
) -> dict | None:
    match = RESPONSE_EVENT_RE.search(body)
    if not match:
        return None
    idx = match.start()
    event_type = match.group(1)

    try:
        event, _ = json.JSONDecoder().raw_decode(body[idx:])
    except json.JSONDecodeError:
        return None

    response = event.get("response") or {}
    usage = response.get("usage") or {}

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
        "status": response.get("status") or event_type,
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
