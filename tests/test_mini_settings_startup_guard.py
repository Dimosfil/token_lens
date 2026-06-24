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

    def test_invalid_mini_settings_recovers_from_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            settings_path.write_text("{broken", encoding="utf-8")
            settings_path.with_name("mini_settings.json.bak").write_text('{"limit": 3}', encoding="utf-8")
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                loaded, save_enabled = mini_client.load_mini_settings_with_status()
                repaired = mini_client.json.loads(settings_path.read_text(encoding="utf-8"))

        self.assertEqual(loaded, {"limit": 3})
        self.assertTrue(save_enabled)
        self.assertEqual(repaired, {"limit": 3})

    def test_invalid_mini_settings_without_backup_allows_new_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "mini_settings.json"
            settings_path.write_text("{broken", encoding="utf-8")
            with mock.patch.object(mini_client, "SETTINGS_PATH", settings_path):
                loaded, save_enabled = mini_client.load_mini_settings_with_status()
                corrupt_files = list(Path(tmp).glob("mini_settings.json.corrupt-*"))

        self.assertEqual(loaded, {})
        self.assertTrue(save_enabled)
        self.assertEqual(len(corrupt_files), 1)

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
