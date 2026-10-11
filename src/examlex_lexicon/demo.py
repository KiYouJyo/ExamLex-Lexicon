"""Small hand-authored demonstration entry; not a dictionary import."""

from __future__ import annotations

import sqlite3


def seed_demo(conn: sqlite3.Connection) -> bool:
    """Add an example 'address' entry without touching existing word data.

    Returns False if an 'address' entry already exists.
    No CEFR level or examination-frequency claims are invented.
    """
    if conn.execute(
        "SELECT 1 FROM entries WHERE language = 'en' "
        "AND normalized_headword = 'address' LIMIT 1"
    ).fetchone():
        return False

    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO sources "
            "(slug, name, url, license_id, redistribution_notes) "
            "VALUES (?, ?, ?, ?, ?)",
            ("local-demo", "ExamLex illustrative sample", None, None,
             "Hand-authored demonstration content; not sourced from a dictionary."),
        )
        source_id = conn.execute(
            "SELECT id FROM sources WHERE slug = 'local-demo'"
        ).fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO entries (headword, normalized_headword, language) "
            "VALUES ('address', 'address', 'en')"
        )
        entry_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO pronunciations (entry_id, part_of_speech, accent, ipa, source_id) "
            "VALUES (?, 'noun', 'en-US', '/ˈæd.res/', ?)",
            (entry_id, source_id),
        )
        conn.execute(
            "INSERT INTO pronunciations (entry_id, part_of_speech, accent, ipa, source_id) "
            "VALUES (?, 'verb', 'en-US', '/əˈdres/', ?)",
            (entry_id, source_id),
        )
        for form_type, form in (
            ("third_person_singular", "addresses"),
            ("past", "addressed"),
            ("past_participle", "addressed"),
            ("present_participle", "addressing"),
        ):
            conn.execute(
                "INSERT INTO inflections (entry_id, part_of_speech, form_type, form, source_id) "
                "VALUES (?, 'verb', ?, ?, ?)",
                (entry_id, form_type, form, source_id),
            )

        noun = conn.execute(
            "INSERT INTO senses (entry_id, part_of_speech, sense_number, definition_en, "
            "source_id) VALUES (?, 'noun', 1, ?, ?)",
            (entry_id, "The details of where someone lives or works.", source_id),
        ).lastrowid
        verb = conn.execute(
            "INSERT INTO senses (entry_id, part_of_speech, sense_number, definition_en, "
            "source_id) VALUES (?, 'verb', 1, ?, ?)",
            (entry_id, "To deal with a problem or issue.", source_id),
        ).lastrowid
        for sense_id, language, translation in (
            (noun, "zh", "地址"),
            (noun, "ja", "住所"),
            (verb, "zh", "处理；应对"),
            (verb, "ja", "対処する"),
        ):
            conn.execute(
                "INSERT INTO sense_translations (sense_id, language, text, source_id) "
                "VALUES (?, ?, ?, ?)",
                (sense_id, language, translation, source_id),
            )
        for expression in ("address a problem", "address an issue", "address a concern"):
            conn.execute(
                "INSERT INTO expressions (sense_id, expression_type, text_en, source_id) "
                "VALUES (?, 'collocation', ?, ?)",
                (verb, expression, source_id),
            )
        example_id = conn.execute(
            "INSERT INTO examples (sense_id, text_en, source_id) VALUES (?, ?, ?)",
            (verb, "The university needs to address students' concerns.", source_id),
        ).lastrowid
        for language, translated in (
            ("zh", "大学需要回应学生的关切。"),
            ("ja", "大学は学生の懸念に対処する必要がある。"),
        ):
            conn.execute(
                "INSERT INTO example_translations (example_id, language, text, source_id) "
                "VALUES (?, ?, ?, ?)",
                (example_id, language, translated, source_id),
            )
    return True
