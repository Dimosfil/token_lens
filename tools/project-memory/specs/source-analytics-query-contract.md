# Source Analytics Query Contract

Updated: 2026-06-30

Token Lens stores normalized usage rows from multiple local sources in the
shared `turns` table, but user-facing analytics must treat each source as a
separate domain. Codex and OpenCode must not share task aggregation rules unless
the rule is explicitly source-neutral.

## Codex

Codex source rows describe Codex turns, response usage events, or post-sampling
context usage estimates. A Codex chat is identified by `thread_id`.

Codex task lists and bucket detail views must aggregate by `thread_id`, not by
`thread_id + turn_id`. One visible Codex task row means one chat:

- `model_calls` is the number of imported Codex usage rows for that chat in the
  selected range;
- `total_tokens` is the sum of imported usage totals for those calls;
- `total_tokens_per_call` is `total_tokens / model_calls`;
- reasoning, input, cached-input, output, and cost fields are summed across the
  chat;
- aggregate rows use `turn_id = "chat:{thread_id}"` so task detail can expand
  all imported calls for the chat.

Codex chat names come from Codex session metadata plus the local Codex
`state_5.sqlite` `threads.title` field when available. The state title should
win over first-message-derived names because it matches the Codex sidebar more
closely. If no usable title exists, UI surfaces may show a stable short
`Chat <thread-id-suffix>` fallback instead of pretending the row has a task
topic.

Codex chat totals should prefer the Codex state `threads.tokens_used` value
when it is greater than the sum of imported usage rows for the same chat. Newer
Codex logs may only expose `post_sampling_token_usage` estimates, which can be
much lower than the account-limit consumption for high-reasoning sessions. Keep
the lower log sum available as diagnostic `log_total_tokens`; expose
`state_tokens_used` when state totals override the log sum.

Raw-only Codex rows are still Codex-specific. They represent chats with recent
raw activity but no usage row and should remain `has_usage = 0`.

## OpenCode

OpenCode source rows describe message or token-tracker usage records. An
OpenCode chat/session is identified by `thread_id`.

OpenCode task lists and bucket detail views also aggregate by `thread_id`, but
they must use OpenCode-specific query paths because OpenCode has no Codex raw
log fallback and does not use Codex invalid-usage filtering. Aggregate rows use
`turn_id = "chat:{thread_id}"` for full-session detail expansion.

## Shared Rules

Range filtering, source filtering, bucket labels, and calendar bucket filling
may be shared helpers. Query functions that define task identity, raw fallback,
invalid usage filtering, detail expansion, or source-specific counters must
remain source-specific.
