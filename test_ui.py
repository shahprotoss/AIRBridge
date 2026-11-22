"""AIRBridge desktop smoke test. No user-visible notifications are emitted."""

import unittest
from unittest.mock import patch

from app import AIRBridgeApp
from transfer_server import Offer


class AIRBridgeUITests(unittest.TestCase):
    def test_main_window_and_completion_notification(self):
        with patch("app.load_config", return_value={"language": "en"}):
            app = AIRBridgeApp()
        app.withdraw()
        try:
            app.update()
            self.assertIn("AIRBridge", app.title())
            self.assertIn("Ready to receive", app.hero_title.cget("text"))
            self.assertTrue(app.qr_image)

            notifications = []
            app._show_toast = lambda title, detail: notifications.append((title, detail))
            app._native_toast = lambda count, total: None
            offer = Offer(id="uitest", peer="127.0.0.1", label="iPhone",
                          files=[{"name": "sample.jpg", "size": 1536}],
                          state="done")
            app._on_complete(offer)
            app.update()
            self.assertEqual(len(notifications), 1)
            self.assertEqual(notifications[0][0], "Transfer complete!")
            self.assertIn("Transfer complete", app.hero_title.cget("text"))
        finally:
            app.close()

    def test_language_switch_updates_controls_and_persists(self):
        with patch("app.load_config", return_value={"language": "en"}):
            app = AIRBridgeApp()
        app.withdraw()
        try:
            with patch("app.save_config") as save:
                app._set_language("Bahasa Melayu")
                app.update()
                self.assertEqual(app.language, "ms")
                self.assertEqual(app.hero_title.cget("text"), "Sedia menerima fail")
                self.assertEqual(app.copy_button.cget("text"), "Salin pautan sambungan    ↗")
                self.assertIn("&lang=ms", app.address_var.get())
                save.assert_called_once_with({
                    "save_dir": str(app.save_dir),
                    "language": "ms",
                })
                app._set_language("English")
                app.update()
                self.assertEqual(app.language, "en")
                self.assertEqual(app.hero_title.cget("text"), "Ready to receive")
                self.assertIn("&lang=en", app.address_var.get())
        finally:
            app.close()

    def test_malay_completion_notification(self):
        with patch("app.load_config", return_value={"language": "ms"}):
            app = AIRBridgeApp()
        app.withdraw()
        try:
            messages = []
            app._show_toast = lambda title, details: messages.append((title, details))
            app._native_toast = lambda count, total: None
            offer = Offer(
                id="ms-test", peer="127.0.0.1", label="iPhone",
                files=[{"name": "gambar.jpg", "size": 2048}],
                state="done",
            )
            app._on_complete(offer)
            app.update()
            self.assertEqual(app.hero_title.cget("text"), "Pemindahan berjaya!")
            self.assertEqual(messages[0][0], "Pemindahan berjaya!")
            self.assertIn("1 fail", messages[0][1])
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
