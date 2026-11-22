"""Regression checks for user downloads: English-first and no raw source."""

from __future__ import annotations

import unittest
import zipfile

from package_airbridge import EXE, PACKAGE_FILES, BASE, ZIP_NAME


class DistributionTests(unittest.TestCase):
    def test_zip_contains_only_windows_app_and_guides(self):
        path = BASE / ZIP_NAME
        self.assertTrue(path.exists(), f"Build the ZIP first: {path}")
        with zipfile.ZipFile(path) as archive:
            self.assertIsNone(archive.testzip())
            actual = set(archive.namelist())
            expected = {name for _, name in PACKAGE_FILES}
            self.assertEqual(actual, expected)
            self.assertIn("AIRBridge/AIRBridge.exe", actual)
            self.assertIn("AIRBridge/START_HERE.txt", actual)
            self.assertIn("AIRBridge/GUIDE_EN.md", actual)
            self.assertIn("AIRBridge/AIRBridge-Guide-EN.png", actual)
            self.assertIn("AIRBridge/Optional-Bahasa-Melayu/GUIDE_BM.md", actual)
            self.assertEqual(
                archive.getinfo("AIRBridge/AIRBridge.exe").file_size,
                EXE.stat().st_size,
            )
            forbidden = (".py", ".js", ".bat", ".html", ".spec", ".pyc")
            for filename in actual:
                self.assertFalse(filename.lower().endswith(forbidden), filename)
                self.assertNotIn("kod-sumber", filename.lower())
                self.assertNotIn("/source/", filename.lower())

    def test_english_is_top_level_and_malay_optional(self):
        with zipfile.ZipFile(BASE / ZIP_NAME) as archive:
            first = archive.read("AIRBridge/START_HERE.txt").decode("utf-8")
            self.assertIn("QUICK START (ENGLISH)", first)
            self.assertIn("English is the default language", first)
            self.assertIn("English is the default", (BASE / "README.md").read_text(encoding="utf-8"))
            self.assertIn("GUIDE_BM.md", archive.namelist()[-2])


if __name__ == "__main__":
    unittest.main()
