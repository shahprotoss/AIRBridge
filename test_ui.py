"""AIRBridge desktop smoke test. No user-visible notifications are emitted."""

import unittest

from app import AIRBridgeApp
from transfer_server import Offer


class AIRBridgeUITests(unittest.TestCase):
    def test_main_window_and_completion_notification(self):
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
            self.assertEqual(notifications[0][0], "Transfer complete")
            self.assertIn("Transfer complete", app.hero_title.cget("text"))
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
