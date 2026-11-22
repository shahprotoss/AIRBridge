"""Offline language coverage tests for the Windows receiver."""
import unittest
from string import Formatter

from localization import LANGUAGES, STRINGS, translate


class LocalizationTests(unittest.TestCase):
    def test_all_keys_exist_in_both_languages(self):
        self.assertEqual(tuple(STRINGS.keys()), LANGUAGES)
        self.assertEqual(set(STRINGS["en"]), set(STRINGS["ms"]))

    def test_placeholders_match(self):
        for key in STRINGS["en"]:
            english = {field for _, field, _, _ in Formatter().parse(STRINGS["en"][key]) if field}
            malay = {field for _, field, _, _ in Formatter().parse(STRINGS["ms"][key]) if field}
            self.assertEqual(english, malay, key)

    def test_translated_feedback(self):
        self.assertEqual(translate("en", "accept"), "Accept")
        self.assertEqual(translate("ms", "accept"), "Terima")
        self.assertEqual(translate("en", "decline"), "Decline")
        self.assertEqual(translate("ms", "decline"), "Tolak")
        self.assertIn("3 fail", translate("ms", "complete_detail", count=3, size="6.0 MB"))
        self.assertIn("3 file(s)", translate("en", "complete_detail", count=3, size="6.0 MB"))


if __name__ == "__main__":
    unittest.main()
