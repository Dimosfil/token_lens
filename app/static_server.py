from __future__ import annotations

import mimetypes
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from app.core.config import ROOT


STATIC_DIR = ROOT / "web"
CONTENT_TYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
}


def serve_static(handler: BaseHTTPRequestHandler, path: str) -> None:
    if path in ("", "/"):
        path = "/index.html"
    candidate = (STATIC_DIR / path.lstrip("/")).resolve()
    if not str(candidate).startswith(str(STATIC_DIR.resolve())) or not candidate.exists():
        handler.send_error(404)
        return
    content_type = CONTENT_TYPES.get(
        candidate.suffix.lower(),
        mimetypes.guess_type(str(candidate))[0] or "application/octet-stream",
    )
    data = candidate.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
