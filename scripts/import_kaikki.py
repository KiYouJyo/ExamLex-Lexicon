#!/usr/bin/env python3
"""Import the selected CEFR A1 headwords / parts of speech from Kaikki JSONL.

The selected word list is supplied locally, not scraped or copied from Oxford.
Works with Kaikki's English Wiktionary export and smaller Simple Wiktionary exports.
No external Python dependencies.

Usage:
 PYTHONPATH=src python scripts/import_kaikki.py \
   --wordlist data/samples/a1_pilot.csv \
   --input path/to/kaikki.jsonl.gz \
   --db build/a1.db --source-kind simple --report build/a1-import.json
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from examlex_lexicon.db import connect_database, initialize_database, validate_database

POS_ALIASES = {
    "n": "noun", "noun": "noun",
    "v": "verb", "verb": "verb", "auxiliary v": "verb", "aux": "verb",
    "adj": "adj", "adjective": "adj",
    "adv": "adv", "adverb": "adv",
    "prep": "prep", "preposition": "prep",
    "pron": "pron", "pronoun": "pron",
    "det": "det", "determiner": "det",
    "conj": "conj", "conjunction": "conj",
    "exclam": "intj", "interj": "intj", "interjection": "intj", "intj": "intj",
    "num": "num", "number": "num", "numeral": "num",
    "article": "article", "indefinite article": "article",
    "modal v": "verb", "modal verb": "verb",
}
BLOCKED_SENSE_TAGS = {"form-of", "alt-of", "obsolete", "archaic", "rare"}
MAX_SENSES_PER_POS = 0  # 0 preserves all eligible source senses
MAX_EXAMPLES_PER_SENSE = 2
MAX_IPA_PER_POS = 6

SOURCES = {
    "en": (
        "kaikki-enwiktionary",
        "Kaikki / English Wiktionary (Wiktextract)",
        "https://kaikki.org/dictionary/English/",
    ),
    "simple": (
        "kaikki-simplewiktionary",
        "Kaikki / Simple English Wiktionary (Wiktextract)",
        "https://kaikki.org/simplewiktionary/",
    ),
}


def normal_pos(value: str) -> str:
    cleaned = value.strip().lower().strip(". ")
    if cleaned not in POS_ALIASES:
        raise ValueError(f"Unrecognized part of speech: {value!r}")
    return POS_ALIASES[cleaned]


def read_targets(path: Path) -> dict[str, set[str]]:
    """Expect UTF-8 CSV: word,pos[,cefr_level]. Repeated words/POS are okay."""
    if not path.is_file():
        raise FileNotFoundError(f"Target wordlist not found: {path}")
    selected: dict[str, set[str]] = defaultdict(set)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not {"word", "pos"}.issubset(reader.fieldnames or []):
            raise ValueError("Wordlist CSV must have 'word' and 'pos' columns.")
        for line, row in enumerate(reader, 2):
            word = (row.get("word") or "").strip()
            pos_text = (row.get("pos") or "").strip()
            cefr = (row.get("cefr_level") or "A1").strip().upper()
            if not word or not pos_text or cefr != "A1":
                raise ValueError(f"Invalid A1 target or POS on CSV line {line}")
            selected[word.casefold()].add(normal_pos(pos_text))
    if not selected:
        raise ValueError("No target words in CSV")
    return dict(selected)


def iter_jsonl(path: Path):
    open_stream = gzip.open if path.name.endswith(".gz") else open
    with open_stream(path, "rt", encoding="utf-8") as file:
        for line_no, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL line {line_no}: {exc}") from exc
            if isinstance(row, dict):
                yield row


def one_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _source(conn: sqlite3.Connection, kind: str) -> int:
    slug, name, url = SOURCES[kind]
    conn.execute(
        "INSERT OR IGNORE INTO sources "
        "(slug, name, url, license_id, attribution, redistribution_notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (slug, name, url, "CC BY-SA / Wiktionary source terms",
         "Wiktionary contributors, via Kaikki.org / Wiktextract",
         "Check Wiktionary attribution and ShareAlike requirements before redistribution."),
    )
    return conn.execute("SELECT id FROM sources WHERE slug=?", (slug,)).fetchone()[0]


def _entry(conn: sqlite3.Connection, word: str, cefr_source: str) -> int:
    norm = word.strip().casefold()
    conn.execute(
        "INSERT INTO entries (headword, normalized_headword, language, cefr_level, cefr_source) "
        "VALUES (?, ?, 'en', 'A1', ?) "
        "ON CONFLICT(language, normalized_headword, homograph_number) DO NOTHING",
        (word.strip(), norm, cefr_source),
    )
    row = conn.execute(
        "SELECT id, cefr_level, cefr_source FROM entries "
        "WHERE normalized_headword=? AND language='en' AND homograph_number=1",
        (norm,),
    ).fetchone()
    # Do not overwrite a reviewed or unrelated CEFR assignment in an existing DB.
    if row["cefr_level"] is None:
        conn.execute(
            "UPDATE entries SET cefr_level='A1', cefr_source=? WHERE id=?",
            (cefr_source, row["id"]),
        )
    elif row["cefr_level"] != "A1":
        raise ValueError(f"Conflict: {word} already has CEFR={row['cefr_level']}")
    return row["id"]


def _nonempty_gloss(sense: dict) -> str | None:
    glosses = sense.get("glosses") or sense.get("raw_glosses") or []
    if not isinstance(glosses, list):
        return None
    # The last nested gloss is typically the most specific meaning.
    for gloss in reversed(glosses):
        text = one_text(gloss)
        if text:
            return text
    return None


def _sense_key(source_object: dict, sense: dict, position: int) -> str:
    explicit = one_text(sense.get("id"))
    if explicit:
        return explicit
    payload = "|".join((
        str(position),
        _nonempty_gloss(sense) or "",
        str(source_object.get("etymology_number") or ""),
    ))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _accent(tags: Any) -> str | None:
    values = {str(x).lower() for x in tags} if isinstance(tags, list) else set()
    if values & {"us", "general-american", "american"}:
        return "en-US"
    if values & {"uk", "british", "received-pronunciation", "southern-england"}:
        return "en-GB"
    return None


def _add_pronunciations(conn: sqlite3.Connection, entry_id: int, pos: str, row: dict, source_id: int) -> int:
    seen: set[tuple] = set()
    count = 0
    sounds = row.get("sounds") or []
    for sound in sounds if isinstance(sounds, list) else []:
        if not isinstance(sound, dict):
            continue
        ipa = one_text(sound.get("ipa"))
        if not ipa or ipa.startswith("[") or len(ipa) > 100:
            continue
        accent = _accent(sound.get("tags"))
        key = (ipa, accent)
        if key in seen:
            continue
        seen.add(key)
        already = conn.execute(
            "SELECT 1 FROM pronunciations WHERE entry_id=? AND part_of_speech=? "
            "AND ipa=? AND accent IS ? LIMIT 1",
            (entry_id, pos, ipa, accent),
        ).fetchone()
        if not already:
            conn.execute(
                "INSERT INTO pronunciations "
                "(entry_id, part_of_speech, accent, ipa, source_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (entry_id, pos, accent, ipa, source_id),
            )
            count += 1
        if len(seen) >= MAX_IPA_PER_POS:
            break
    return count


def _add_forms(conn: sqlite3.Connection, entry_id: int, pos: str, row: dict, source_id: int) -> int:
    count = 0
    forms = row.get("forms") or []
    for form in forms[:50] if isinstance(forms, list) else []:
        if not isinstance(form, dict):
            continue
        spelling = one_text(form.get("form"))
        tags = form.get("tags") or []
        if not spelling or spelling in ("-", "?") or spelling.casefold() == row["word"].casefold():
            continue
        if not isinstance(tags, list):
            tags = []
        tags = [str(tag) for tag in tags if isinstance(tag, str) and tag.strip()]
        if not tags:
            continue
        ftype = ";".join(sorted(set(tags)))[:200]
        exists = conn.execute(
            "SELECT 1 FROM inflections WHERE entry_id=? AND part_of_speech=? "
            "AND form_type=? AND form=?",
            (entry_id, pos, ftype, spelling),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO inflections "
                "(entry_id, part_of_speech, form_type, form, source_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (entry_id, pos, ftype, spelling, source_id),
            )
            count += 1
    return count


def _add_examples(conn: sqlite3.Connection, sense_id: int, sense: dict, source_id: int) -> int:
    count = 0
    examples = sense.get("examples") or []
    for example in examples if isinstance(examples, list) else []:
        if not isinstance(example, dict):
            continue
        # Avoid lengthy, separately copyrighted literature quotations.
        if example.get("type") == "quotation" or example.get("ref"):
            continue
        text = one_text(example.get("text"))
        if not text or len(text) > 350:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO examples "
            "(sense_id, text_en, source_id, review_status) VALUES (?, ?, ?, 'imported')",
            (sense_id, text, source_id),
        )
        count += 1
        if count >= MAX_EXAMPLES_PER_SENSE:
            break
    return count


def _add_relations(conn: sqlite3.Connection, sense_id: int, sense: dict, source_id: int) -> int:
    total = 0
    for relation, name in (("synonym", "synonyms"), ("antonym", "antonyms")):
        items = sense.get(name) or []
        for item in items[:30] if isinstance(items, list) else []:
            word = one_text(item.get("word")) if isinstance(item, dict) else None
            if not word or len(word) > 100:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO semantic_relations "
                "(sense_id, relation_type, related_word, source_id) "
                "VALUES (?, ?, ?, ?)", (sense_id, relation, word, source_id),
            )
            total += 1
    return total


def _upsert_record(
    conn: sqlite3.Connection, row: dict, pos: str, source_id: int, counter: Counter,
    cefr_source: str,
) -> None:
    word = row["word"].strip()
    entry_id = _entry(conn, word, cefr_source)
    counter["headword_pos_records"] += 1
    counter["pronunciations_inserted"] += _add_pronunciations(conn, entry_id, pos, row, source_id)
    counter["forms_inserted"] += _add_forms(conn, entry_id, pos, row, source_id)
    source_key = f"{word.casefold()}:{pos}:ety={row.get('etymology_number') or 0}"
    raw_senses = row.get("senses") or []
    for position, sense in enumerate(raw_senses if isinstance(raw_senses, list) else []):
        if not isinstance(sense, dict):
            continue
        tags = sense.get("tags") or []
        if isinstance(tags, list) and BLOCKED_SENSE_TAGS.intersection(tags):
            continue
        gloss = _nonempty_gloss(sense)
        if not gloss:
            continue
        key = _sense_key(row, sense, position)
        mapped = conn.execute(
            "SELECT sense_id FROM source_links "
            "WHERE source_id=? AND source_entry_key=? AND source_sense_key=?",
            (source_id, source_key, key),
        ).fetchone()
        if mapped:
            counter["existing_source_senses"] += 1
            continue
        same = conn.execute(
            "SELECT id FROM senses WHERE entry_id=? AND part_of_speech=? "
            "AND definition_en=? LIMIT 1", (entry_id, pos, gloss),
        ).fetchone()
        if same:
            sense_id = same["id"]
        else:
            total = conn.execute(
                "SELECT COUNT(*) FROM senses WHERE entry_id=? AND part_of_speech=?",
                (entry_id, pos),
            ).fetchone()[0]
            if MAX_SENSES_PER_POS and total >= MAX_SENSES_PER_POS:
                counter["excess_senses_skipped"] += 1
                continue
            next_number = conn.execute(
                "SELECT COALESCE(MAX(sense_number), 0) + 1 FROM senses "
                "WHERE entry_id=? AND part_of_speech=?", (entry_id, pos),
            ).fetchone()[0]
            sense_id = conn.execute(
                "INSERT INTO senses "
                "(entry_id, part_of_speech, sense_number, definition_en, source_id, review_status) "
                "VALUES (?, ?, ?, ?, ?, 'imported')",
                (entry_id, pos, next_number, gloss, source_id),
            ).lastrowid
            counter["senses_inserted"] += 1

        conn.execute(
            "INSERT INTO source_links "
            "(source_id, source_entry_key, source_sense_key, entry_id, sense_id, match_status) "
            "VALUES (?, ?, ?, ?, ?, 'matched')",
            (source_id, source_key, key, entry_id, sense_id),
        )
        counter["examples_inserted"] += _add_examples(conn, sense_id, sense, source_id)
        counter["relations_seen"] += _add_relations(conn, sense_id, sense, source_id)


def import_words(
    database: Path, wordlist: Path, input_file: Path,
    source_kind: str = "en", max_entries: int = 0,
    cefr_source: str = "Local A1 selection (unverified source)",
) -> dict:
    targets = read_targets(wordlist)
    if not input_file.is_file():
        raise FileNotFoundError(f"Kaikki JSONL not found: {input_file}")
    initialize_database(database)
    stats: Counter = Counter()
    matched: set[str] = set()
    matched_pos: set[tuple[str, str]] = set()
    with connect_database(database) as conn:
        source_id = _source(conn, source_kind)
        conn.commit()
        for row in iter_jsonl(input_file):
            stats["lines_read"] += 1
            if row.get("lang_code") != "en":
                continue
            word = row.get("word")
            if not isinstance(word, str):
                continue
            norm = word.strip().casefold()
            if norm not in targets:
                continue
            raw_pos = str(row.get("pos") or "")
            try:
                pos = normal_pos(raw_pos)
            except ValueError:
                stats["unknown_pos_skipped"] += 1
                continue
            if pos not in targets[norm]:
                stats["unselected_pos_skipped"] += 1
                continue
            if max_entries and norm not in matched and len(matched) >= max_entries:
                continue
            with conn:
                _upsert_record(conn, row, pos, source_id, stats, cefr_source)
            matched.add(norm)
            matched_pos.add((norm, pos))
        stats["matched_unique_words"] = len(matched)
        stats["target_unique_words"] = len(targets)
        stats["missing_unique_words"] = len(targets.keys() - matched)
        all_pos = {(w, p) for w, pos_set in targets.items() for p in pos_set}
        missing_pos = sorted(all_pos - matched_pos)
        stats["target_word_pos_pairs"] = len(all_pos)
        stats["matched_word_pos_pairs"] = len(matched_pos)
        stats["missing_word_pos_pairs"] = len(missing_pos)
        valid = validate_database(conn)
        if not valid["ok"]:
            raise RuntimeError(f"Validation failed after import: {valid}")
        counts = valid["counts"]
    report = {
        "source": SOURCES[source_kind][0],
        "source_file": str(input_file),
        "targets": len(targets),
        "matched": len(matched),
        "missing": sorted(targets.keys() - matched),
        "missing_word_pos": [{"word": w, "pos": p} for w, p in missing_pos],
        "matched_word_pos": len(matched_pos),
        "target_word_pos": len(all_pos),
        "cefr_source": cefr_source,
        "statistics": dict(sorted(stats.items())),
        "database_counts": counts,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wordlist", type=Path, required=True,
                        help="Local word, pos, cefr_level CSV; not bundled full Oxford list")
    parser.add_argument("--input", type=Path, required=True,
                        help="Kaikki JSONL or .jsonl.gz export")
    parser.add_argument("--db", type=Path, default=Path("build/a1.db"))
    parser.add_argument("--source-kind", choices=SOURCES, default="en")
    parser.add_argument("--max-entries", type=int, default=0)
    parser.add_argument("--cefr-source", default="Local A1 selection (unverified source)",
                        help="Text describing who verified the A1 selection; never invented")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.max_entries < 0:
        parser.error("--max-entries must be >= 0")
    try:
        report = import_words(
            args.db, args.wordlist, args.input, args.source_kind, args.max_entries,
            args.cefr_source,
        )
    except (OSError, ValueError, sqlite3.Error, RuntimeError) as exc:
        parser.exit(2, f"Import failed: {exc}\n")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
