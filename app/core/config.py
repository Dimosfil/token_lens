from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.json"
LOCAL_CONFIG_PATH = ROOT / "config.local.json"


def load_config() -> dict:
    config = _read_json(CONFIG_PATH)
    if LOCAL_CONFIG_PATH.exists():
        config.update(_read_json(LOCAL_CONFIG_PATH))

    for key in ("analytics_db", "codex_logs_db", "codex_session_index"):
        if config.get(key):
            config[key] = str(_resolve_config_path(config[key]))

    return config


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_config_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path
