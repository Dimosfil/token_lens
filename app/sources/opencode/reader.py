from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator


def iter_messages_after(db_path: str, last_rowid: int = 0) -> Iterator[dict]:
    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        rows = source.execute(
            """
            select m.rowid as _rowid,
                   m.id,
                   m.session_id,
                   m.time_created,
                   m.data,
                   s.title as session_title,
                   s.directory as session_directory
            from message m
            join session s on m.session_id = s.id
            where m.rowid > ?
            order by m.rowid
            """,
            [last_rowid],
        )
        for row in rows:
            yield dict(row)
    finally:
        source.close()


def read_jsonl_after(jsonl_path: str, offset: int = 0) -> Iterator[tuple[dict, int]]:
    try:
        file_size = os.path.getsize(jsonl_path)
    except OSError:
        return

    if file_size < offset:
        offset = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        f.seek(offset)
        while True:
            line = f.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield record, f.tell()


def jsonl_file_size(jsonl_path: str) -> int:
    try:
        return os.path.getsize(jsonl_path)
    except OSError:
        return 0
