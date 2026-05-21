from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout = 10000")
    con.execute("pragma journal_mode = WAL")
    con.execute("pragma synchronous = NORMAL")
    return con
