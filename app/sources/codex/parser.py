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
RESPONSE_CREATE_REQUEST_MARKERS = (
    'websocket request: {"type":"response.create"',
    'websocket request: {"type": "response.create"',
)
USAGE_INSTRUMENT = 'instrument_name="codex.turn.token_usage"'
POST_SAMPLING_USAGE_RE = re.compile(
    r"^(?P<trace>(?:[A-Za-z0-9_.-]+\{[^{}]*\}:)*turn\{[^{}]*\})"
    r":session_task\.run:run_turn: post sampling token usage (?P<fields>[^\r\n]*)"
)
POST_SAMPLING_INT_RE = re.compile(
    r"\b(total_usage_tokens|auto_compact_scope_tokens|auto_compact_scope_limit)=([0-9]+)\b"
)
ESTIMATED_TOKEN_COUNT_RE = re.compile(r"\bestimated_token_count=Some\(([0-9]+)\)")


def compact_json(value) -> str | None:
    if value in (None, "", [], {}):
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def response_output_payload(response: dict):
    output = response.get("output")
    if output not in (None, "", [], {}):
        return output
    for key in ("output_text", "content"):
        if response.get(key):
            return response.get(key)
    return None


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


def build_turn_row(
    *,
    source_log_id: int,
    response_id: str | None,
    status: str,
    ts: int,
    thread_id: str,
    thread_names: dict[str, str],
    turn_id: str,
    submission_id: str | None,
    model: str,
    reasoning_effort: str | None,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
    reasoning_output_tokens: int,
    total_tokens: int,
    prices: dict,
    non_cached_input_tokens: int | None = None,
) -> dict:
    dt = datetime.fromtimestamp(ts, timezone.utc)
    row = {
        "source_log_id": source_log_id,
        "source": "codex",
        "response_id": response_id,
        "status": status,
        "ts": ts,
        "ts_iso": dt.isoformat(),
        "day": dt.date().isoformat(),
        "thread_id": thread_id,
        "thread_name": thread_names.get(thread_id),
        "turn_id": turn_id,
        "submission_id": submission_id,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "non_cached_input_tokens": (
            non_cached_input_tokens
            if non_cached_input_tokens is not None
            else max(input_tokens - cached_input_tokens, 0)
        ),
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_output_tokens,
        "total_tokens": total_tokens,
        "request_json": None,
        "response_json": None,
        "event_json": None,
    }
    row["estimated_cost"] = estimate_cost(row, prices)
    row["imported_at"] = datetime.now(timezone.utc).isoformat()
    return row


def usage_response_id(thread_id: str, turn_id: str, model: str) -> str:
    return f"codex-usage:{thread_id}:{turn_id}:{model}"


def estimated_usage_response_id(thread_id: str, turn_id: str, model: str) -> str:
    return f"codex-estimate:{thread_id}:{turn_id}:{model}"


def usage_event_segment(body: str) -> str | None:
    stripped = body.lstrip()
    if stripped.startswith(USAGE_INSTRUMENT):
        return stripped.splitlines()[0] if stripped.splitlines() else stripped
    return None


def parse_post_sampling_usage_row(
    source_log_id: int,
    ts: int,
    thread_id: str | None,
    body: str,
    thread_names: dict[str, str],
    prices: dict,
) -> dict | None:
    match = POST_SAMPLING_USAGE_RE.match(body.lstrip())
    if not match:
        return None

    trace = match.group("trace")
    fields = match.group("fields")
    int_fields = {name: int(value) for name, value in POST_SAMPLING_INT_RE.findall(fields)}
    total_tokens = int_fields.get("total_usage_tokens", 0)
    if total_tokens <= 0:
        return None

    resolved_thread_id = first_match(THREAD_RE, trace) or thread_id
    turn_id = first_match(TURN_RE, trace)
    model = first_match(MODEL_RE, trace)
    if not resolved_thread_id or not turn_id or not model:
        return None

    row = build_turn_row(
        source_log_id=source_log_id,
        response_id=estimated_usage_response_id(resolved_thread_id, turn_id, model),
        status="estimated",
        ts=ts,
        thread_id=resolved_thread_id,
        thread_names=thread_names,
        turn_id=turn_id,
        submission_id=first_match(SUBMISSION_RE, trace),
        model=model,
        reasoning_effort=first_match(EFFORT_RE, trace),
        input_tokens=total_tokens,
        cached_input_tokens=0,
        non_cached_input_tokens=total_tokens,
        output_tokens=0,
        reasoning_output_tokens=0,
        total_tokens=total_tokens,
        prices=prices,
    )
    estimated_match = ESTIMATED_TOKEN_COUNT_RE.search(fields)
    row["event_json"] = compact_json({
        "type": "codex.post_sampling_token_usage",
        "total_usage_tokens": total_tokens,
        "auto_compact_scope_tokens": int_fields.get("auto_compact_scope_tokens"),
        "estimated_token_count": int(estimated_match.group(1)) if estimated_match else None,
        "auto_compact_scope_limit": int_fields.get("auto_compact_scope_limit"),
    })
    return row


def parse_usage_row(
    source_log_id: int,
    ts: int,
    thread_id: str | None,
    body: str,
    thread_names: dict[str, str],
    prices: dict,
) -> dict | None:
    estimated_row = parse_post_sampling_usage_row(
        source_log_id,
        ts,
        thread_id,
        body,
        thread_names,
        prices,
    )
    if estimated_row:
        return estimated_row

    segment = usage_event_segment(body)
    if not segment:
        return None

    token_pairs = {name: int(value) for name, value in TOKEN_RE.findall(segment)}
    if not token_pairs:
        return None

    resolved_thread_id = first_match(THREAD_RE, segment) or thread_id
    turn_id = first_match(TURN_RE, segment)
    model = first_match(MODEL_RE, segment)
    if not resolved_thread_id or not turn_id or not model:
        return None

    input_tokens = token_pairs.get("input_tokens", 0)
    cached_input_tokens = token_pairs.get("cached_input_tokens", 0)
    non_cached_input_tokens = token_pairs.get("non_cached_input_tokens")
    if non_cached_input_tokens is not None:
        cached_input_tokens = max(input_tokens - non_cached_input_tokens, 0)
    output_tokens = token_pairs.get("output_tokens", 0)
    reasoning_output_tokens = token_pairs.get("reasoning_output_tokens", 0)
    total_tokens = token_pairs.get("total_tokens", 0)
    if (
        total_tokens <= 0
        or total_tokens < input_tokens + output_tokens
        or not any((input_tokens, cached_input_tokens, output_tokens, reasoning_output_tokens))
    ):
        return None

    return build_turn_row(
        source_log_id=source_log_id,
        response_id=usage_response_id(resolved_thread_id, turn_id, model),
        status="completed",
        ts=ts,
        thread_id=resolved_thread_id,
        thread_names=thread_names,
        turn_id=turn_id,
        submission_id=first_match(SUBMISSION_RE, segment),
        model=model,
        reasoning_effort=first_match(EFFORT_RE, segment),
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        non_cached_input_tokens=non_cached_input_tokens,
        output_tokens=output_tokens,
        reasoning_output_tokens=reasoning_output_tokens,
        total_tokens=total_tokens,
        prices=prices,
    )


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
    if not usage:
        return None
    request_payload = response.get("input") or event.get("input") or event.get("request")
    response_payload = response_output_payload(response) or response

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
    if total_tokens <= 0:
        return None

    row = build_turn_row(
        source_log_id=source_log_id,
        response_id=response.get("id"),
        status=response.get("status") or event_type,
        ts=ts,
        thread_id=resolved_thread_id,
        thread_names=thread_names,
        turn_id=turn_id,
        submission_id=first_match(SUBMISSION_RE, body),
        model=model,
        reasoning_effort=first_match(EFFORT_RE, body),
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        non_cached_input_tokens=None,
        output_tokens=output_tokens,
        reasoning_output_tokens=reasoning_tokens,
        total_tokens=total_tokens,
        prices=prices,
    )
    row["request_json"] = compact_json(request_payload)
    row["response_json"] = compact_json(response_payload)
    row["event_json"] = compact_json(event)
    return row


def parse_response_create_request(
    source_log_id: int,
    ts: int,
    thread_id: str | None,
    body: str,
) -> dict | None:
    if not any(marker in body for marker in RESPONSE_CREATE_REQUEST_MARKERS):
        return None

    marker = "websocket request: "
    marker_index = body.find(marker)
    if marker_index < 0:
        return None

    try:
        payload, _ = json.JSONDecoder().raw_decode(body[marker_index + len(marker):])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("type") != "response.create":
        return None

    resolved_thread_id = first_match(THREAD_RE, body) or thread_id
    turn_id = first_match(TURN_RE, body)
    model = payload.get("model") or first_match(MODEL_RE, body)
    if not resolved_thread_id or not turn_id or not model:
        return None

    return {
        "source_log_id": source_log_id,
        "ts": ts,
        "thread_id": resolved_thread_id,
        "turn_id": turn_id,
        "model": model,
        "request_json": compact_json(payload),
    }
