from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.services import analytics_service
from app.sources.codex.session_transcript import load_turn_payloads


class CodexSessionTranscriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sessions = Path(self.tmp.name) / "sessions"
        self.session_dir = self.sessions / "2026" / "07" / "17"
        self.session_dir.mkdir(parents=True)
        self.thread_id = "019f6eef-ae6c-79b1-9d07-f6b02114c151"
        self.turn_id = "019f6eef-d266-7a42-9a53-7da6d1342d46"
        self.path = self.session_dir / f"rollout-test-{self.thread_id}.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def write_rows(self, rows: list[dict]) -> None:
        self.path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_loads_exact_turn_user_and_assistant_messages(self):
        self.write_rows([
            {"type": "session_meta", "payload": {"id": self.thread_id}},
            {
                "timestamp": "2026-07-17T07:17:18Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": self.turn_id},
            },
            {
                "timestamp": "2026-07-17T07:17:19Z",
                "type": "event_msg",
                "payload": {
                    "type": "user_message",
                    "message": "first request",
                    "local_images": ["C:\\Temp\\image.png"],
                },
            },
            {
                "timestamp": "2026-07-17T07:17:20Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "phase": "commentary",
                    "content": [{"type": "output_text", "text": "working"}],
                },
            },
            {"malformed": "known but irrelevant"},
            {
                "timestamp": "2026-07-17T07:17:21Z",
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "steering request"},
            },
            {
                "timestamp": "2026-07-17T07:17:22Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "phase": "final_answer",
                    "content": [{"type": "output_text", "text": "finished"}],
                },
            },
            {
                "timestamp": "2026-07-17T07:17:23Z",
                "type": "event_msg",
                "payload": {"type": "task_complete", "turn_id": self.turn_id},
            },
            {
                "timestamp": "2026-07-17T07:17:24Z",
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "outside turn"},
            },
        ])

        payloads = load_turn_payloads(str(self.sessions), self.thread_id, {self.turn_id})

        request = payloads[self.turn_id]["request"]
        response = payloads[self.turn_id]["response"]
        self.assertEqual([item["text"] for item in request["messages"]], [
            "first request",
            "steering request",
        ])
        self.assertEqual(request["messages"][0]["local_images"], ["C:\\Temp\\image.png"])
        self.assertEqual([item["text"] for item in response["messages"]], ["working", "finished"])
        self.assertEqual([item["phase"] for item in response["messages"]], ["commentary", "final_answer"])

    def test_rejects_unsafe_thread_id_and_wrong_session_metadata(self):
        self.write_rows([
            {"type": "session_meta", "payload": {"id": "different-thread-id"}},
            {
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": self.turn_id},
            },
            {
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "private"},
            },
        ])

        self.assertEqual(load_turn_payloads(str(self.sessions), self.thread_id, {self.turn_id}), {})
        self.assertEqual(load_turn_payloads(str(self.sessions), "../../sessions", {self.turn_id}), {})

    def test_service_fills_only_missing_payloads(self):
        detail = {
            "task": {"thread_id": self.thread_id},
            "calls": [
                {
                    "source": "codex",
                    "turn_id": self.turn_id,
                    "request": None,
                    "response": {"stored": True},
                },
            ],
        }
        transcript_payload = {
            self.turn_id: {
                "request": {"source": "codex_session_transcript", "messages": [{"text": "request"}]},
                "response": {"source": "codex_session_transcript", "messages": [{"text": "replacement"}]},
            },
        }

        with mock.patch.object(analytics_service, "load_turn_payloads", return_value=transcript_payload):
            result = analytics_service._add_codex_session_payloads(
                detail,
                str(self.sessions),
                self.thread_id,
            )

        call = result["calls"][0]
        self.assertEqual(call["request"]["messages"][0]["text"], "request")
        self.assertEqual(call["request_source"], "codex_session_transcript")
        self.assertEqual(call["response"], {"stored": True})
        self.assertNotIn("response_source", call)


if __name__ == "__main__":
    unittest.main()
