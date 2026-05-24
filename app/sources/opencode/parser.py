from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from app.sources.codex.parser import compact_json, estimate_cost


USAGE_KEYS = {"input_tokens", "output_tokens", "total_tokens"}


def stable_source_log_id(payload: dict) -> int:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.blake2b(encoded, digest_size=8).digest()
    value = int.from_bytes(digest, "big") & ((1 << 63) - 1)
    return -max(value, 1)


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def first_value(value: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        for key in keys:
            if value.get(key) not in (None, ""):
                return value[key]
        for item in value.values():
            found = first_value(item, keys)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for item in value:
            found = first_value(item, keys)
            if found not in (None, ""):
                return found
    return None


def first_usage(value: Any) -> dict | None:
    if isinstance(value, dict):
        if USAGE_KEYS & set(value):
            return value
        for key in ("usage", "tokens", "token_usage", "tokenUsage"):
            nested = value.get(key)
            if isinstance(nested, dict) and (USAGE_KEYS & set(nested)):
                return nested
        for item in value.values():
            found = first_usage(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = first_usage(item)
            if found:
                return found
    return None


def timestamp_seconds(payload: dict) -> int:
    value = (
        payload.get("ts")
        or payload.get("timestamp")
        or first_value(payload.get("event"), ("time", "timestamp", "created", "updated"))
    )
    if isinstance(value, (int, float)):
        return int(value / 1000) if value > 10_000_000_000 else int(value)
    if isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00")
            return int(datetime.fromisoformat(normalized).timestamp())
        except ValueError:
            return int(datetime.now(timezone.utc).timestamp())
    return int(datetime.now(timezone.utc).timestamp())


def detail_tokens(usage: dict, detail_key: str, token_key: str) -> int:
    details = usage.get(detail_key)
    if isinstance(details, dict):
        return int_value(details.get(token_key))
    return 0


def parse_opencode_event(payload: dict, prices: dict) -> dict | None:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    usage = first_usage(payload)
    if not usage:
        return None

    input_tokens = int_value(usage.get("input_tokens") or usage.get("input") or usage.get("prompt_tokens"))
    output_tokens = int_value(usage.get("output_tokens") or usage.get("output") or usage.get("completion_tokens"))
    total_tokens = int_value(usage.get("total_tokens") or usage.get("total"), input_tokens + output_tokens)
    if total_tokens == 0 and input_tokens == 0 and output_tokens == 0:
        return None

    cached_tokens = int_value(
        usage.get("cached_input_tokens")
        or usage.get("cache_read_input_tokens")
        or usage.get("cached_tokens")
    )
    if cached_tokens == 0:
        cached_tokens = detail_tokens(usage, "input_tokens_details", "cached_tokens")
    reasoning_tokens = int_value(usage.get("reasoning_output_tokens") or usage.get("reasoning_tokens"))
    if reasoning_tokens == 0:
        reasoning_tokens = detail_tokens(usage, "output_tokens_details", "reasoning_tokens")

    ts = timestamp_seconds(payload)
    dt = datetime.fromtimestamp(ts, timezone.utc)
    session_id = (
        first_value(event, ("sessionID", "session_id"))
        or first_value(payload, ("sessionID", "session_id"))
        or first_value(event.get("session") if isinstance(event, dict) else None, ("id",))
        or "opencode-session"
    )
    message_id = first_value(event, ("messageID", "message_id", "partID", "part_id", "id")) or session_id
    model = first_value(payload, ("model", "modelID", "model_id")) or "opencode/unknown"
    event_type = event.get("type") if isinstance(event, dict) else payload.get("type")
    response_id = f"opencode:{message_id}"

    row = {
        "source_log_id": stable_source_log_id({
            "source": "opencode",
            "session": session_id,
            "message": message_id,
            "type": event_type,
            "ts": ts,
            "usage": usage,
        }),
        "source": "opencode",
        "response_id": response_id,
        "status": str(event_type or "completed"),
        "ts": ts,
        "ts_iso": dt.isoformat(),
        "day": dt.date().isoformat(),
        "thread_id": str(session_id),
        "thread_name": first_value(payload, ("title", "name")) or payload.get("directory") or "OpenCode session",
        "turn_id": str(message_id),
        "submission_id": first_value(event, ("requestID", "request_id")),
        "model": str(model),
        "reasoning_effort": first_value(payload, ("variant", "reasoning_effort")),
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "non_cached_input_tokens": max(input_tokens - cached_tokens, 0),
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_tokens,
        "total_tokens": total_tokens or input_tokens + output_tokens,
        "request_json": compact_json(first_value(payload, ("input", "request", "prompt"))),
        "response_json": compact_json(first_value(payload, ("output", "response", "message"))),
        "event_json": compact_json(payload),
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    row["estimated_cost"] = estimate_cost(row, prices)
    return row
