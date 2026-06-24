from __future__ import annotations

from datetime import datetime, timezone
import json
import queue
import shutil
import subprocess
import threading
import time

from app.core.codex_discovery import discover_codex_command


DEFAULT_CACHE_SECONDS = 30
DEFAULT_TIMEOUT_SECONDS = 20

_CACHE: dict | None = None
_CACHE_TS = 0.0


def read_usage_limits(config: dict | None = None) -> dict:
    config = config or {}
    if config.get("codex_rate_limits_enabled") is False:
        return _unavailable("disabled")

    cache_seconds = _safe_int(config.get("codex_rate_limits_cache_seconds"), DEFAULT_CACHE_SECONDS, 1, 300)
    now = time.time()
    global _CACHE, _CACHE_TS
    if _CACHE and now - _CACHE_TS < cache_seconds:
        cached = dict(_CACHE)
        cached["cached"] = True
        return cached

    command = _resolve_codex_command(config)
    if not command:
        return _unavailable("codex command not found")

    timeout_seconds = _safe_int(config.get("codex_rate_limits_timeout_seconds"), DEFAULT_TIMEOUT_SECONDS, 3, 60)
    try:
        result = _request_rate_limits(command, timeout_seconds)
    except Exception as error:
        return _unavailable(str(error))

    if result.get("error"):
        return _unavailable(_error_message(result["error"]))

    snapshot = _normalize_rate_limits(result.get("result") or {})
    _CACHE = snapshot
    _CACHE_TS = time.time()
    return snapshot


def _resolve_codex_command(config: dict) -> str | None:
    configured = str(config.get("codex_app_server_command") or "").strip()
    if configured:
        return configured
    return discover_codex_command() or shutil.which("codex.cmd") or shutil.which("codex")


def _request_rate_limits(command: str, timeout_seconds: int) -> dict:
    creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    proc = subprocess.Popen(
        [command, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        creationflags=creation_flags,
    )
    lines: queue.Queue[str | None] = queue.Queue()
    reader = threading.Thread(target=_read_stdout_lines, args=(proc, lines), daemon=True)
    reader.start()

    try:
        _write_message(proc, {
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "token_lens",
                    "title": "Token Lens",
                    "version": "0.1.0",
                },
            },
        })
        deadline = time.time() + timeout_seconds
        sent_read = False
        while time.time() < deadline:
            try:
                line = lines.get(timeout=0.25)
            except queue.Empty:
                if proc.poll() is not None:
                    break
                continue
            if line is None:
                break
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == 1 and not sent_read:
                _write_message(proc, {"method": "initialized", "params": {}})
                _write_message(proc, {"id": 2, "method": "account/rateLimits/read", "params": None})
                sent_read = True
                continue
            if message.get("id") == 2:
                return message
        return {"error": {"message": "codex app-server rate limit request timed out"}}
    finally:
        _stop_process(proc)


def _read_stdout_lines(proc: subprocess.Popen, lines: queue.Queue[str | None]) -> None:
    if proc.stdout is None:
        lines.put(None)
        return
    for line in proc.stdout:
        lines.put(line.strip())
    lines.put(None)


def _write_message(proc: subprocess.Popen, message: dict) -> None:
    if proc.stdin is None:
        raise RuntimeError("codex app-server stdin is unavailable")
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.kill()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def _normalize_rate_limits(result: dict) -> dict:
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
    return {
        "ok": True,
        "source": "codex_app_server",
        "cached": False,
        "fetched_at": _iso_from_ts(now),
        "limit_id": snapshot.get("limitId"),
        "limit_name": snapshot.get("limitName"),
        "plan_type": snapshot.get("planType"),
        "rate_limit_reached_type": snapshot.get("rateLimitReachedType"),
        "credits": snapshot.get("credits"),
        "groups": groups,
        "windows": windows,
        "limit_ids": sorted(buckets.keys()),
    }


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
    used_percent = _safe_int(window.get("usedPercent"), 0, 0, 100)
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


def _safe_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(max(number, minimum), maximum)


def _unavailable(message: str) -> dict:
    return {
        "ok": False,
        "source": "codex_app_server",
        "cached": False,
        "error": message,
        "windows": [],
    }


def _error_message(error) -> str:
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)
