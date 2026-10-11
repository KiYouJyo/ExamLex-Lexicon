"""Import-pipeline regression tests (fixtures are synthetic, not dictionary data)."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "import_kaikki", ROOT / "scripts" / "import_kaikki.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

from examlex_lexicon.db import connect_database, lookup_word, validate_database


class ImportPipelineTests(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workdir.cleanup)
        self.db = Path(self.workdir.name) / "pilot.db"
        self.targets = Path(self.workdir.name) / "targets.csv"
        self.targets.write_text(
            "word,pos,cefr_level\napple,noun,A1\naddress,noun,A1\n",
            encoding="utf-8",
        )
        self.source = ROOT / "tests" / "fixtures" / "kaikki_a1.jsonl"

    def test_import_filters_pos_and_languages_and_is_idempotent(self):
        result = MODULE.import_words(self.db, self.targets, self.source)
        self.assertEqual(result["matched"], 2)
        self.assertEqual(result["database_counts"]["senses"], 2)
        self.assertIn("address", result["statistics"] and ["address"])
        with connect_database(self.db) as conn:
            apple = lookup_word(conn, "apple")
            self.assertEqual(apple["cefr_level"], "A1")
            self.assertEqual(apple["cefr_source"],
                             "Oxford A1 (locally supplied selection)")
            self.assertEqual(apple["senses"][0]["part_of_speech"], "noun")
            self.assertEqual(len(apple["senses"][0]["examples"]), 1)
            self.assertEqual(apple["inflections"][0]["form"], "apples")
            self.assertEqual(apple["pronunciations"][0]["ipa"], "/ˈæp.əl/")
            address = lookup_word(conn, "address")
            self.assertEqual(len(address["senses"]), 1)
            self.assertEqual(address["senses"][0]["part_of_speech"], "noun")
            self.assertIsNone(lookup_word(conn, "cat"))
            self.assertTrue(validate_database(conn)["ok"])

        result2 = MODULE.import_words(self.db, self.targets, self.source)
        self.assertEqual(result2["database_counts"], result["database_counts"])
        self.assertGreater(result2["statistics"]["existing_source_senses"], 0)

    def test_rejects_unexpected_cefr_and_unknown_pos(self):
        self.targets.write_text("word,pos,cefr_level\napple,noun,B1\n",
                                encoding="utf-8")
        with self.assertRaises(ValueError):
            MODULE.read_targets(self.targets)
        self.targets.write_text("word,pos,cefr_level\napple,unknown,A1\n",
                                encoding="utf-8")
        with self.assertRaises(ValueError):
            MODULE.read_targets(self.targets)

    def test_conflicting_cefr_is_not_overwritten(self):
        MODULE.import_words(self.db, self.targets, self.source)
        with connect_database(self.db) as conn:
            conn.execute(
                "UPDATE entries SET cefr_level='B2' "
                "WHERE normalized_headword='address'"
            )
            conn.commit()
        with self.assertRaises(ValueError):
            MODULE.import_words(self.db, self.targets, self.source)

    def test_missing_word_report(self):
        self.targets.write_text("word,pos,cefr_level\napple,noun,A1\nzzyyzz,noun,A1\n",
                                encoding="utf-8")
        report = MODULE.import_words(self.db, self.targets, self.source)
        self.assertEqual(report["missing"], ["zzyyzz"])
        self.assertEqual(report["matched"], 1)


if __name__ == "__main__":
    unittest.main()
