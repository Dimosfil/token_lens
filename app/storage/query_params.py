from __future__ import annotations


DEFAULT_RANGE = "7d"
DEFAULT_BUCKET = "day"
CUSTOM_RANGE = "custom"
TASK_MODE_AGGREGATE = "aggregate"
TASK_MODE_SEPARATE = "separate"
SEPARATE_TASK_RANGES = {"1h", "24h"}

RANGE_SECONDS = {
    "1h": 60 * 60,
    "24h": 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
    "30d": 30 * 24 * 60 * 60,
    "365d": 365 * 24 * 60 * 60,
}

BUCKET_SECONDS = {
    "hour": 60 * 60,
    "day": 24 * 60 * 60,
    "month": 30 * 24 * 60 * 60,
}

BUCKETS = {
    "hour": "strftime('%Y-%m-%d %H:00', ts, 'unixepoch', 'localtime')",
    "day": "day",
    "month": "substr(day, 1, 7)",
}

MAX_BUCKETS = {
    ("1h", "hour"): 1,
    ("24h", "hour"): 24,
    ("24h", "day"): 1,
    ("7d", "hour"): 7 * 24,
    ("7d", "day"): 7,
    ("30d", "hour"): 30 * 24,
    ("30d", "day"): 30,
    ("30d", "month"): 1,
    ("365d", "hour"): 365 * 24,
    ("365d", "day"): 365,
    ("365d", "month"): 12,
}


def normalize_range(range_key: str = "") -> str:
    if range_key == CUSTOM_RANGE:
        return CUSTOM_RANGE
    return range_key if range_key in RANGE_SECONDS else DEFAULT_RANGE


def normalize_bucket(bucket: str = DEFAULT_BUCKET, range_key: str = DEFAULT_RANGE) -> str:
    if normalize_range(range_key) == CUSTOM_RANGE:
        return bucket if bucket in BUCKET_SECONDS else DEFAULT_BUCKET
    range_seconds = RANGE_SECONDS[normalize_range(range_key)]
    bucket_seconds = BUCKET_SECONDS.get(bucket)
    if bucket_seconds and bucket_seconds <= range_seconds:
        return bucket
    return DEFAULT_BUCKET if BUCKET_SECONDS[DEFAULT_BUCKET] <= range_seconds else "hour"


def normalize_task_mode(task_mode: str = "", range_key: str = DEFAULT_RANGE) -> str:
    if task_mode == TASK_MODE_SEPARATE and normalize_range(range_key) in SEPARATE_TASK_RANGES:
        return TASK_MODE_SEPARATE
    return TASK_MODE_AGGREGATE
