from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FullLauncherContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / "start.ps1").read_text(encoding="utf-8")

    def test_startup_health_uses_lightweight_state(self):
        self.assertIn("/api/state?include_raw=0", self.script)
        self.assertIn("launcher_api_timeout_seconds", self.script)

    def test_launcher_groups_process_trees_and_repairs_duplicates(self):
        self.assertIn("function Get-TokenLensProcessRoots", self.script)
        self.assertIn("multiple independent process trees", self.script)
        self.assertIn("adopted existing process tree root", self.script)

    def test_partial_startup_rolls_back_current_invocation(self):
        self.assertIn("function Undo-StartedApps", self.script)
        self.assertIn("Undo-StartedApps", self.script.rsplit("catch {", 1)[1])

    def test_ready_requires_api_and_mini_window_verification(self):
        self.assertIn("Assert-SingleTokenLensTree", self.script)
        self.assertIn("no window was verified", self.script)
        self.assertIn("Token Lens app set ready", self.script)


if __name__ == "__main__":
    unittest.main()
