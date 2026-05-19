from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    analytics_db = Path(config["analytics_db"])
    if not analytics_db.is_absolute():
        analytics_db = ROOT / analytics_db
    config["analytics_db"] = str(analytics_db)

    return config
