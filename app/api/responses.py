from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler


def send_json(handler: BaseHTTPRequestHandler, payload) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
