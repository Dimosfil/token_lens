# Call Detail Modal Plan

Created: 2026-05-21

## Goal

Open a detail modal from task/call rows. Show task metadata, every model call for
the selected turn, and request/response detail for the selected call.

## Checklist

- [x] Add storage columns for imported call detail payloads.
- [x] Add query/service/API route for task detail by `thread_id` + `turn_id`.
- [x] Add frontend modal and row click handlers.
- [x] Verify compile/tests and update this checklist.
