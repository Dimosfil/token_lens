from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
create table if not exists turns (
  source_log_id integer primary key,
  response_id text unique,
  ts integer not null,
  ts_iso text not null,
  day text not null,
  thread_id text not null,
  thread_name text,
  turn_id text not null,
  submission_id text,
  model text not null,
  reasoning_effort text,
  input_tokens integer not null default 0,
  cached_input_tokens integer not null default 0,
  non_cached_input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  reasoning_output_tokens integer not null default 0,
  total_tokens integer not null default 0,
  estimated_cost real not null default 0,
  imported_at text not null
);

create index if not exists idx_turns_ts on turns(ts);
create index if not exists idx_turns_day on turns(day);
create index if not exists idx_turns_model on turns(model);
create index if not exists idx_turns_thread on turns(thread_id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path: str) -> None:
    with connect(db_path) as con:
        con.executescript(SCHEMA)
        columns = {row["name"] for row in con.execute("pragma table_info(turns)").fetchall()}
        if "response_id" not in columns:
            con.execute("alter table turns add column response_id text")
            con.execute("create unique index if not exists idx_turns_response_id on turns(response_id)")
