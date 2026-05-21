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
