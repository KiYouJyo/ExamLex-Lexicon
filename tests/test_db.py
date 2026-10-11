"""Run: PYTHONPATH=src python -m unittest discover -s tests -v"""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from examlex_lexicon.cli import main
from examlex_lexicon.db import (
    connect_database,
    initialize_database,
    lookup_word,
    validate_database,
)
from examlex_lexicon.demo import seed_demo


class LexiconDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "nested" / "examlex.db"
        initialize_database(self.path)
        self.conn = connect_database(self.path)
        self.addCleanup(self.conn.close)

    def test_init_and_reinit(self):
        self.assertEqual(self.conn.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        initialize_database(self.path)
        self.assertTrue(validate_database(self.conn)["ok"])

    def test_every_required_table_exists(self):
        existing = {
            row[0] for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue({
            "sources", "entries", "pronunciations", "inflections",
            "senses", "sense_translations", "semantic_relations",
            "expressions", "examples", "example_translations",
            "exam_tags", "source_links",
        }.issubset(existing))

    def test_cefr_levels_simple_and_optional(self):
        self.conn.execute(
            "INSERT INTO entries (headword, normalized_headword) VALUES (?, ?)",
            ("word", "word"),
        )
        self.assertIsNone(
            self.conn.execute(
                "SELECT cefr_level FROM entries WHERE headword = 'word'"
            ).fetchone()[0]
        )
        self.conn.execute(
            "UPDATE entries SET cefr_level = 'B2', cefr_source = 'editorial' "
            "WHERE headword = 'word'"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE entries SET cefr_level = 'D1' WHERE headword = 'word'"
            )

    def test_unique_entries_and_homographs(self):
        self.conn.execute(
            "INSERT INTO entries (headword, normalized_headword) "
            "VALUES ('Example', 'example')"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO entries (headword, normalized_headword) "
                "VALUES ('example', 'example')"
            )
        self.conn.execute(
            "INSERT INTO entries (headword, normalized_headword, homograph_number) "
            "VALUES ('example', 'example', 2)"
        )

    def test_foreign_keys_are_enforced(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO senses (entry_id, part_of_speech, sense_number) "
                "VALUES (999999, 'noun', 1)"
            )

    def test_demo_word_is_sense_aligned_and_idempotent(self):
        self.assertTrue(seed_demo(self.conn))
        self.assertFalse(seed_demo(self.conn))
        word = lookup_word(self.conn, " ADDRESS ")
        self.assertIsNotNone(word)
        self.assertIsNone(word["cefr_level"])
        self.assertEqual(word["headword"], "address")
        self.assertEqual(len(word["pronunciations"]), 2)
        self.assertEqual(len(word["inflections"]), 4)
        self.assertEqual(len(word["senses"]), 2)
        noun, verb = word["senses"]
        self.assertEqual(noun["part_of_speech"], "noun")
        self.assertEqual(verb["part_of_speech"], "verb")
        self.assertEqual(
            {t["language"]: t["text"] for t in noun["translations"]},
            {"zh": "地址", "ja": "住所"},
        )
        self.assertEqual(
            {t["language"]: t["text"] for t in verb["translations"]},
            {"zh": "处理；应对", "ja": "対処する"},
        )
        self.assertEqual(len(verb["expressions"]), 3)
        self.assertEqual(len(verb["examples"]), 1)
        self.assertEqual(len(verb["examples"][0]["translations"]), 2)
        self.assertEqual(len(noun["examples"]), 0)
        self.assertTrue(validate_database(self.conn)["ok"])

    def test_source_link_mismatch_is_detected(self):
        seed_demo(self.conn)
        other_id = self.conn.execute(
            "INSERT INTO entries (headword, normalized_headword) "
            "VALUES ('other', 'other')"
        ).lastrowid
        verb_id = lookup_word(self.conn, "address")["senses"][1]["id"]
        source_id = self.conn.execute(
            "SELECT id FROM sources WHERE slug = 'local-demo'"
        ).fetchone()[0]
        self.conn.execute(
            "INSERT INTO source_links "
            "(source_id, source_entry_key, source_sense_key, entry_id, sense_id) "
            "VALUES (?, 'other', 'sense-1', ?, ?)",
            (source_id, other_id, verb_id),
        )
        report = validate_database(self.conn)
        self.assertFalse(report["ok"])
        self.assertEqual(report["mismatched_source_links"], 1)

    def test_wrong_schema_version_is_rejected(self):
        self.conn.execute("PRAGMA user_version = 99")
        with self.assertRaises(ValueError):
            initialize_database(self.path)

    def test_missing_database_does_not_create_file(self):
        absent = Path(self.temp.name) / "absent.db"
        with self.assertRaises(FileNotFoundError):
            connect_database(absent)
        self.assertFalse(absent.exists())

    def test_cli_round_trip(self):
        path = Path(self.temp.name) / "cli.db"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--db", str(path), "init"]), 0)
            self.assertEqual(main(["--db", str(path), "seed-demo"]), 0)
            self.assertEqual(main(["--db", str(path), "lookup", "address"]), 0)
        self.assertIn('"headword": "address"', out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--db", str(path), "validate"]), 0)
        self.assertTrue(json.loads(out.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
