from __future__ import annotations

import argparse
import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = ROOT / "tools" / "project-memory"
DB_PATH = MEMORY_DIR / "project_memory.sqlite"
NOTES_PATH = MEMORY_DIR / "NOTES.md"

INDEXED_SUFFIXES = {".md", ".py", ".js", ".html", ".css", ".json", ".ps1"}
SKIP_DIRS = {".git", "__pycache__", "data", ".venv", "venv"}

SCHEMA = """
create table if not exists files (
  path text primary key,
  extension text not null,
  size_bytes integer not null,
  sha256 text not null,
  modified_at text not null,
  indexed_at text not null,
  excerpt text not null
);

create table if not exists notes (
  id integer primary key autoincrement,
  created_at text not null,
  topic text not null,
  title text not null,
  body text not null,
  evidence_paths text not null
);

create table if not exists commands (
  command text primary key,
  purpose text not null,
  last_result text not null,
  updated_at text not null
);
"""


@dataclass
class RebuildStats:
    indexed: int = 0
    skipped: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with connect() as con:
        con.executescript(SCHEMA)


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def iter_indexable_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(ROOT).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if path.suffix.lower() not in INDEXED_SUFFIXES:
            continue
        yield path


def read_excerpt(path: Path, max_chars: int = 4000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars]


def rebuild() -> RebuildStats:
    init_db()
    stats = RebuildStats()
    indexed_at = utc_now()
    seen: set[str] = set()

    with connect() as con:
        for path in iter_indexable_files():
            try:
                data = path.read_bytes()
                rel_path = relative(path)
                seen.add(rel_path)
                stat = path.stat()
                con.execute(
                    """
                    insert or replace into files (
                      path, extension, size_bytes, sha256, modified_at,
                      indexed_at, excerpt
                    ) values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rel_path,
                        path.suffix.lower(),
                        stat.st_size,
                        hashlib.sha256(data).hexdigest(),
                        datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        indexed_at,
                        read_excerpt(path),
                    ),
                )
                stats.indexed += 1
            except OSError:
                stats.skipped += 1

        existing = [row["path"] for row in con.execute("select path from files").fetchall()]
        for old_path in existing:
            if old_path not in seen:
                con.execute("delete from files where path = ?", (old_path,))

    return stats


def add_note(topic: str, title: str, body: str, evidence: list[str]) -> None:
    init_db()
    with connect() as con:
        con.execute(
            """
            insert into notes (created_at, topic, title, body, evidence_paths)
            values (?, ?, ?, ?, ?)
            """,
            (utc_now(), topic, title, body, "\n".join(evidence)),
        )


def export_notes() -> None:
    init_db()
    with connect() as con:
        rows = con.execute(
            "select created_at, topic, title, body, evidence_paths from notes order by id"
        ).fetchall()

    lines = [
        "# Project Memory Notes",
        "",
        "SQLite agent memory is a local generated search/index layer.",
        "This Markdown file is the human-reviewable durable export.",
        "",
    ]
    if not rows:
        lines += ["No notes recorded yet.", ""]
    for row in rows:
        lines += [
            f"## {row['title']}",
            "",
            f"- Topic: {row['topic']}",
            f"- Created: {row['created_at']}",
            f"- Evidence: {row['evidence_paths'] or 'none'}",
            "",
            row["body"],
            "",
        ]
    NOTES_PATH.write_text("\n".join(lines), encoding="utf-8")


def stats() -> dict[str, int | str]:
    init_db()
    with connect() as con:
        file_count = con.execute("select count(*) as n from files").fetchone()["n"]
        note_count = con.execute("select count(*) as n from notes").fetchone()["n"]
        command_count = con.execute("select count(*) as n from commands").fetchone()["n"]
    return {
        "database": str(DB_PATH),
        "files": file_count,
        "notes": note_count,
        "commands": command_count,
    }


def search(query: str, limit: int) -> list[sqlite3.Row]:
    init_db()
    like = f"%{query}%"
    with connect() as con:
        return con.execute(
            """
            select path, extension, size_bytes
            from files
            where path like ? or excerpt like ?
            order by path
            limit ?
            """,
            (like, like, limit),
        ).fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description="Token Lens agent-memory SQLite CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("rebuild")
    sub.add_parser("stats")
    search_parser = sub.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=10)
    note_parser = sub.add_parser("note")
    note_parser.add_argument("topic")
    note_parser.add_argument("title")
    note_parser.add_argument("body")
    note_parser.add_argument("--evidence", action="append", default=[])
    sub.add_parser("export-notes")
    args = parser.parse_args()

    if args.command == "init":
        init_db()
        print(f"Initialized {DB_PATH}")
    elif args.command == "rebuild":
        result = rebuild()
        print(f"Indexed {result.indexed} files; skipped {result.skipped}.")
    elif args.command == "stats":
        for key, value in stats().items():
            print(f"{key}: {value}")
    elif args.command == "search":
        for row in search(args.query, args.limit):
            print(f"{row['path']} ({row['extension']}, {row['size_bytes']} bytes)")
    elif args.command == "note":
        add_note(args.topic, args.title, args.body, args.evidence)
        export_notes()
        print("Note saved and exported.")
    elif args.command == "export-notes":
        export_notes()
        print(f"Exported {NOTES_PATH}")


if __name__ == "__main__":
    main()
