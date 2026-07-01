# Codex Usage Import Contract

Updated: 2026-06-30

Token Lens imports Codex token usage from local Codex logs into
`data/analytics.sqlite` as read-only source data. Codex log bodies can contain
assistant responses, command output, tests, docs, or source code that mention
`codex.turn.token_usage.*` or `post sampling token usage`; those mentions are
not usage telemetry.

## Parser Boundary

`parse_usage_row()` may accept synthetic `codex-usage:*` or
`codex-estimate:*` rows only when the token fields come from one of these
telemetry contexts:

- a standalone old-format log event whose body starts with
  `instrument_name="codex.turn.token_usage"`;
- a Codex initial trace prefix followed immediately by
  `:session_task.run:run_turn: post sampling token usage ...`.

It must reject token-usage strings that appear only inside response text,
command output, file listings, tests, docs, or quoted snippets. The parser must
extract `thread.id`, `turn.id`, `model`, `submission.id`, reasoning effort, and
token fields from the accepted telemetry segment, not from unrelated later text
in the same log body.

`post sampling token usage` rows are context-usage estimates rather than exact
OpenAI response usage payloads. Token Lens stores them with
`status="estimated"`, `response_id="codex-estimate:{thread}:{turn}:{model}"`,
and `total_tokens=input_tokens=total_usage_tokens`. Output, cached-input, and
reasoning token fields remain zero unless Codex emits exact response usage for
that turn.

Completed `response.*` events without a non-empty usage payload, or with
`total_tokens <= 0`, are not usage rows and must not create model calls.

## Import Cursor

The Codex import cursor records the last scanned source log id in
`codex_import_state.last_scanned_source_log_id`. It must advance across skipped
rows as well as imported rows. Using only the latest imported turn source id is
incorrect because a run with many non-usage rows would rescan the same text and
could later import stale quoted snippets if the parser contract changes.

## Existing Data Repair

If this contract changes, existing `turns` rows with
`response_id like 'codex-usage:%'`, `response_id like 'codex-estimate:%'`, or
zero token totals must be revalidated against the archived
`raw_logs.feedback_log_body` or the current Codex source log row. Rows that no
longer parse under the contract should be deleted from `turns`; raw archive rows
should be kept. In particular, older trace-only `turn{...codex.turn.token_usage...}`
synthetic rows must be removed because they can report cumulative multi-million
totals that do not correspond to one request payload.

## Verification

Regression coverage must include a log body where response output quotes
`codex.turn.token_usage.input_tokens=742224` and
`codex.turn.token_usage.total_tokens=743544`; this body must not import as a
usage row. Coverage must also include a response output that quotes a full
`post sampling token usage` line; this body must not import as an estimate.
A live repair check should verify:

- no Codex `turns` row has the false-positive `total_tokens=743544`;
- no Codex `turns` row has `total_tokens=0`;
- current-day Codex dashboard data has no huge rows from quoted snippets;
- all remaining `codex-usage:*` and `codex-estimate:*` rows reparse
  successfully under the current contract.
