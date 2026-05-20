# Project Memory Notes

SQLite agent memory is a local generated search/index layer.
This Markdown file is the human-reviewable durable export.

## Application stack

- Topic: architecture
- Created: 2026-05-20T04:41:51.712104+00:00
- Evidence: tools/project-memory/architecture.md
app/server.py
app/db.py
web/app.js
config.json

Token Lens uses a Python standard-library backend, ThreadingHTTPServer, SQLite product database, vanilla HTML/CSS/JS frontend, PowerShell runtime scripts, JSON configuration, and a separate local SQLite database for agent memory.
