from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.storage.connection import connect


@dataclass(frozen=True)
class RawLogRetentionResult:
    cutoff_day: str
    cleared_rows: int = 0
    applied: bool = False


def retention_cutoff_day(months: int = 1, now: datetime | None = None) -> str:
    if months < 1:
        raise ValueError("raw log body retention months must be at least 1")

    current = now or datetime.now(timezone.utc)
    month_index = current.year * 12 + current.month - months
    year, zero_based_month = divmod(month_index, 12)
    return f"{year:04d}-{zero_based_month + 1:02d}-01"


def apply_raw_log_retention(
    db_path: str,
    *,
    months: int = 1,
    batch_size: int = 100_000,
    now: datetime | None = None,
) -> RawLogRetentionResult:
    if batch_size < 1:
        raise ValueError("raw log retention batch size must be at least 1")

    cutoff_day = retention_cutoff_day(months, now)
    con = connect(db_path)
    try:
        state = con.execute(
            "select last_cutoff_day from raw_log_retention_state where id = 1"
        ).fetchone()
        if state and str(state["last_cutoff_day"]) >= cutoff_day:
            return RawLogRetentionResult(cutoff_day=cutoff_day)

        cleared_rows = _clear_old_bodies(con, cutoff_day, batch_size)
        con.execute(
            """
            insert into raw_log_retention_state (id, last_cutoff_day, updated_at)
            values (1, ?, ?)
            on conflict(id) do update set
              last_cutoff_day = excluded.last_cutoff_day,
              updated_at = excluded.updated_at
            """,
            [cutoff_day, datetime.now(timezone.utc).isoformat()],
        )
        con.commit()
        return RawLogRetentionResult(
            cutoff_day=cutoff_day,
            cleared_rows=cleared_rows,
            applied=True,
        )
    finally:
        con.close()


def _clear_old_bodies(con, cutoff_day: str, batch_size: int) -> int:
    last_source_log_id = -1
    cleared_rows = 0
    while True:
        rows = con.execute(
            """
            select source_log_id
            from raw_logs
            where source_log_id > ?
              and day < ?
              and length(feedback_log_body) > 0
            order by source_log_id
            limit ?
            """,
            [last_source_log_id, cutoff_day, batch_size],
        ).fetchall()
        if not rows:
            break

        batch_end_id = int(rows[-1]["source_log_id"])
        cursor = con.execute(
            """
            update raw_logs
            set feedback_log_body = ''
            where source_log_id > ?
              and source_log_id <= ?
              and day < ?
              and length(feedback_log_body) > 0
            """,
            [last_source_log_id, batch_end_id, cutoff_day],
        )
        con.commit()
        cleared_rows += cursor.rowcount
        last_source_log_id = batch_end_id
    return cleared_rows
