"""PDF text parser regression tests use synthetic, non-Oxford lines."""
import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts" / "prepare_oxford_a1.py"
spec = importlib.util.spec_from_file_location("prepare_oxford_a1", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class LocalPdfParserTests(unittest.TestCase):
    def test_a1_parts_of_speech_and_a2_exclusion(self):
        rows = module.parse_a1_lines([
            "The Oxford 3000 by CEFR level",
            "A1", "a, an indefinite article", "apple n.",
            "answer n., v.", "can¹ modal v.", "bank (money) n.",
            "above prep., adv.", "be v., auxiliary v.", "A2",
            "abandon v.",
        ])
        for expected in [
            ("a", "article"), ("an", "article"), ("apple", "noun"),
            ("answer", "noun"), ("answer", "verb"), ("can", "verb"),
            ("bank", "noun"), ("above", "adv"), ("be", "verb")
        ]:
            self.assertIn(expected, rows)
        self.assertNotIn(("abandon", "verb"), rows)

    def test_missing_cefr_heading_rejected(self):
        with self.assertRaises(ValueError):
            module.parse_a1_lines(["Apple n.", "A2"])
