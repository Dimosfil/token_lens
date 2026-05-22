from __future__ import annotations

import json


def decode_json(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


COMPACT_RESPONSE_EVENT_KEYS = {
    "id",
    "object",
    "created_at",
    "status",
    "completed_at",
    "error",
    "incomplete_details",
    "model",
    "parallel_tool_calls",
    "previous_response_id",
    "reasoning",
    "service_tier",
    "usage",
}


def compact_event_payload(value):
    if not isinstance(value, dict):
        return value
    response = value.get("response")
    if not isinstance(response, dict):
        return value

    compacted = {
        key: response[key]
        for key in COMPACT_RESPONSE_EVENT_KEYS
        if key in response
    }
    omitted = sorted(
        key for key in response
        if key not in COMPACT_RESPONSE_EVENT_KEYS
    )

    event = dict(value)
    event["response"] = compacted
    if omitted:
        event["compacted"] = True
        event["omitted_response_fields"] = omitted
    return event
