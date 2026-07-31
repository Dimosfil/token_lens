from __future__ import annotations

from datetime import datetime, timezone
import time


def normalize_rate_limits(result: dict) -> dict:
    primary_snapshot = result.get("rateLimits") or {}
    buckets = result.get("rateLimitsByLimitId") or {}
    now = int(time.time())
    snapshots = []
    if isinstance(buckets, dict) and buckets:
        for limit_id in sorted(buckets):
            snapshot = buckets.get(limit_id)
            if isinstance(snapshot, dict):
                snapshots.append(snapshot)
    elif isinstance(primary_snapshot, dict) and primary_snapshot:
        snapshots.append(primary_snapshot)

    groups = [_normalize_limit_group(snapshot, now) for snapshot in snapshots]
    groups = [group for group in groups if group["windows"]]
    windows = [window for group in groups for window in group["windows"]]
    snapshot = primary_snapshot if isinstance(primary_snapshot, dict) else {}
    fetched_at = _iso_from_ts(now)
    return {
        "ok": True,
        "source": "codex_app_server",
        "cached": False,
        "stale": False,
        "fetched_at": fetched_at,
        "last_success_at": fetched_at,
        "limit_id": snapshot.get("limitId"),
        "limit_name": snapshot.get("limitName"),
        "plan_type": snapshot.get("planType"),
        "rate_limit_reached_type": snapshot.get("rateLimitReachedType"),
        "credits": snapshot.get("credits"),
        "groups": groups,
        "windows": windows,
        "limit_ids": sorted(buckets.keys()),
    }


def safe_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(max(number, minimum), maximum)


def _normalize_limit_group(snapshot: dict, now: int) -> dict:
    limit_id = snapshot.get("limitId")
    limit_name = snapshot.get("limitName")
    display_name = str(limit_name or "Codex")
    windows = []
    for key, fallback_label in (("primary", "5h"), ("secondary", "weekly")):
        window = snapshot.get(key)
        if isinstance(window, dict):
            windows.append(_normalize_window(
                key,
                fallback_label,
                window,
                now,
                str(limit_id or ""),
                str(limit_name or ""),
                display_name,
            ))
    return {
        "limit_id": limit_id,
        "limit_name": limit_name,
        "display_name": display_name,
        "plan_type": snapshot.get("planType"),
        "rate_limit_reached_type": snapshot.get("rateLimitReachedType"),
        "credits": snapshot.get("credits"),
        "windows": windows,
    }


def _normalize_window(
    key: str,
    fallback_label: str,
    window: dict,
    now: int,
    limit_id: str,
    limit_name: str,
    display_name: str,
) -> dict:
    used_percent = safe_int(window.get("usedPercent"), 0, 0, 100)
    reset_ts = window.get("resetsAt")
    reset_seconds = None
    reset_at = None
    if isinstance(reset_ts, int):
        reset_seconds = max(0, reset_ts - now)
        reset_at = _iso_from_ts(reset_ts)
    duration_mins = window.get("windowDurationMins")
    return {
        "key": key,
        "limit_id": limit_id,
        "limit_name": limit_name,
        "display_name": display_name,
        "label": _window_label(duration_mins, fallback_label),
        "window_duration_mins": duration_mins,
        "used_percent": used_percent,
        "remaining_percent": max(0, min(100, 100 - used_percent)),
        "reset_at": reset_at,
        "reset_seconds": reset_seconds,
    }


def _window_label(duration_mins, fallback: str) -> str:
    if duration_mins == 300:
        return "5h"
    if duration_mins == 10080:
        return "weekly"
    if isinstance(duration_mins, int) and duration_mins >= 60 and duration_mins % 60 == 0:
        return f"{duration_mins // 60}h"
    return fallback


def _iso_from_ts(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
