"""Offline tests for full English Kaikki per-word source selection."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_kaikki_english_words as source


class KaikkiPerWordTests(unittest.TestCase):
    def test_about_url_points_to_full_english(self):
        self.assertEqual(
            source.word_jsonl_url("about"),
            "https://kaikki.org/dictionary/English/meaning/a/ab/about.jsonl",
        )
        self.assertEqual(
            source.word_jsonl_url("be"),
            "https://kaikki.org/dictionary/English/meaning/b/be/be.jsonl",
        )

    def test_parts_of_speech_are_not_inferred_or_rewritten(self):
        objects = [
            {"word": "about", "lang_code": "en", "pos": "prep",
             "senses": [{"glosses": ["Regarding."]}]},
            {"word": "about", "lang_code": "en", "pos": "adv",
             "senses": [{"glosses": ["Approximately."]}]},
            {"word": "about", "lang_code": "fr", "pos": "adv",
             "senses": [{"glosses": ["Wrong language."]}]},
        ]
        blob = ("\n".join(json.dumps(obj) for obj in objects) + "\n").encode()
        with patch.object(source, "_get_data", return_value=blob):
            lines, missing = source._fetch_word("about", {"prep", "adv"})
            self.assertIsNone(missing)
            self.assertEqual({json.loads(line)["pos"] for line in lines}, {"prep", "adv"})
            lines, missing = source._fetch_word("about", {"noun"})
            self.assertEqual(lines, [])
            self.assertEqual(missing, "no_requested_part_of_speech")

    def test_download_report_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            words = root / "words.csv"
            words.write_text(
                "word,pos,cefr_level\nabout,prep,A1\nabout,adv,A1\n"
                "apple,noun,A1\n", encoding="utf-8")
            payload = (json.dumps({
                "word": "about", "lang_code": "en", "pos": "adv",
                "senses": [{"glosses": ["Approximately."]}]},
            ) + "\n").encode()
            with patch.object(
                source, "_get_data",
                side_effect=lambda url: None if "apple.jsonl" in url else payload,
            ):
                result = source.download_selected(
                    words, root / "out.jsonl", root / "report.json", workers=1)
            self.assertEqual(result["downloaded_matching_words"], 1)
            self.assertEqual(result["missing_or_no_matching_pos"]["apple"], "not_found")
            self.assertEqual(len((root / "out.jsonl").read_text().splitlines()), 1)
            self.assertEqual(json.loads((root / "report.json").read_text())
                             ["downloaded_records"], 1)


if __name__ == "__main__":
    unittest.main()
