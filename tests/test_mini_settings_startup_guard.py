from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from desktop import mini_client


class MiniSettingsStartupGuardTests(unittest.TestCase):
    def test_missing_mini_settings_allows_first_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                loaded, save_enabled = mini_client.load_mini_settings_with_status()

        self.assertEqual(loaded, {})
        self.assertTrue(save_enabled)

    def test_invalid_mini_settings_disables_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            settings_path.write_text("{broken", encoding="utf-8")
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                loaded, save_enabled = mini_client.load_mini_settings_with_status()

        self.assertEqual(loaded, {})
        self.assertFalse(save_enabled)

    def test_disabled_settings_save_does_not_overwrite(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.settings_after_id = "pending"
        app.settings_save_enabled = False
        app.settings_save_ready = True

        with mock.patch.object(mini_client, "save_mini_settings") as save:
            app.save_settings_now()

        self.assertIsNone(app.settings_after_id)
        save.assert_not_called()

    def test_settings_save_waits_until_startup_is_ready(self):
        app = mini_client.MiniClientApp.__new__(mini_client.MiniClientApp)
        app.closed = False
        app.settings_after_id = None
        app.settings_save_enabled = True
        app.settings_save_ready = False

        app.schedule_settings_save()
        with mock.patch.object(mini_client, "save_mini_settings") as save:
            app.save_settings_now()

        self.assertIsNone(app.settings_after_id)
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
