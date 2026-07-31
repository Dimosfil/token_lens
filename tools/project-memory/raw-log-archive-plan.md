# Raw Log Archive Plan

Created: 2026-05-21

## Goal

Persist every newly seen Codex log row into Token Lens' own SQLite database
during the existing automatic import loop, and make raw response events reliable
enough for per-call token-waste analysis.

## Checklist

- [x] Add `raw_logs` storage table and repository helpers.
- [x] Add source reader for all log rows after the last archived id.
- [x] Extend import stats and service flow to archive raw rows automatically.
- [x] Add tests and run verification.
- [x] Backfill or reimport older usage rows so `turns.event_json` is populated
      whenever the source Codex log contains a raw response event.
- [x] Add a call-detail indicator for `raw event captured` / `missing`.
- [ ] Add a later `Token suspects` view or endpoint based on raw event fields
      such as instructions, tools, schema, metadata, previous response chains,
      cached input ratio, and in-progress/zero-token calls.
- [ ] Add a later `Analyze token waste` action that sends the full raw event
      plus computed measurements to the analyzer.

## Maintenance Rule

Token Lens automatically retains full `raw_logs.feedback_log_body` values only
for the configured current calendar-month window. The default
`raw_log_body_retention_months` value is `1`. At the first Codex import for a
new cutoff month, the retention service clears older bodies in bounded batches
and records the applied cutoff in `raw_log_retention_state`. Any delayed older
source row imported later is archived with an empty body immediately.

Retention must not delete `raw_logs` rows, touch `turns`, or alter
token/model/day analytics. Repair flows must treat an empty retained body as
unavailable evidence, not as proof that an existing analytics row is invalid.

For manual bulk maintenance, clear only `raw_logs.feedback_log_body` in
`data/analytics.sqlite` for days outside the retained calendar-month window.

After a manual bulk update transaction commits, run `VACUUM` so SQLite returns
the freed pages to disk. Automatic monthly passes avoid a blocking full-file
rewrite; their freed pages remain reusable by SQLite until the next controlled
manual compaction. Verify:

- rows outside the current month with non-empty `feedback_log_body`: `0`;
- current-month rows still have non-empty `feedback_log_body`;
- `turns` and `raw_logs` row counts were not intentionally reduced.
