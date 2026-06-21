from __future__ import annotations

from .connection import connect


SCHEMA = """
create table if not exists turns (
  source_log_id integer primary key,
  source text not null default 'codex',
  response_id text unique,
  status text not null default 'completed',
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
  request_json text,
  response_json text,
  event_json text,
  imported_at text not null
);

create index if not exists idx_turns_ts on turns(ts);
create index if not exists idx_turns_day on turns(day);
create index if not exists idx_turns_model on turns(model);
create index if not exists idx_turns_thread on turns(thread_id);

create table if not exists raw_logs (
  source_log_id integer primary key,
  ts integer not null,
  ts_iso text not null,
  day text not null,
  thread_id text,
  feedback_log_body text not null,
  archived_at text not null
);

create index if not exists idx_raw_logs_ts on raw_logs(ts);
create index if not exists idx_raw_logs_thread on raw_logs(thread_id);

create table if not exists raw_log_archive_state (
  id integer primary key check (id = 1),
  last_source_log_id integer not null default 0,
  updated_at text not null
);

create table if not exists opencode_import_state (
  id integer primary key check (id = 1),
  last_rowid integer not null default 0,
  last_jsonl_offset integer not null default 0,
  last_jsonl_size integer not null default 0,
  updated_at text not null
);
"""


def init_db(db_path: str) -> None:
    con = connect(db_path)
    try:
        con.executescript(SCHEMA)
        columns = {row["name"] for row in con.execute("pragma table_info(turns)").fetchall()}
        if "response_id" not in columns:
            con.execute("alter table turns add column response_id text")
            con.execute("create unique index if not exists idx_turns_response_id on turns(response_id)")
        if "source" not in columns:
            con.execute("alter table turns add column source text not null default 'codex'")
            con.execute(
                "update turns set source = 'opencode' where source_log_id < 0 or response_id like 'opencode:%'"
            )
        if "status" not in columns:
            con.execute("alter table turns add column status text not null default 'completed'")
        for detail_column in ("request_json", "response_json", "event_json"):
            if detail_column not in columns:
                con.execute(f"alter table turns add column {detail_column} text")
        con.execute("create index if not exists idx_turns_source on turns(source)")
        con.commit()
    finally:
        con.close()
