"""SQLite initialization, validation and small read-only lookup helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import SCHEMA_VERSION

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "schema.sql"


def connect_database(db_path: str | Path, *, must_exist: bool = True) -> sqlite3.Connection:
    """Open a SQLite file with FK enforcement. Avoid creating files for reads."""
    path = Path(db_path)
    if must_exist and not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}. Run 'init' first.")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(db_path: str | Path) -> None:
    """Create a v1 database. Re-running is safe; newer schemas are rejected."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_database(path, must_exist=False) as conn:
        old_version = conn.execute("PRAGMA user_version").fetchone()[0]
        if old_version not in (0, SCHEMA_VERSION):
            raise ValueError(
                f"Unsupported schema version {old_version}; expected {SCHEMA_VERSION}."
            )
        if not SCHEMA_PATH.is_file():
            raise FileNotFoundError(f"Schema file missing: {SCHEMA_PATH}")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise RuntimeError(f"Database initialization failed: v{version}")


def _rows(conn: sqlite3.Connection, query: str, values: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(query, values).fetchall()]


def lookup_word(conn: sqlite3.Connection, word: str) -> dict | None:
    """Return a JSON-ready, sense-aligned entry for exact casefolded lookup."""
    normalized = word.strip().casefold()
    row = conn.execute(
        "SELECT * FROM entries WHERE language = 'en' AND normalized_headword = ? "
        "ORDER BY homograph_number LIMIT 1",
        (normalized,),
    ).fetchone()
    if row is None:
        return None

    entry = dict(row)
    entry_id = entry["id"]
    entry["pronunciations"] = _rows(
        conn, "SELECT * FROM pronunciations WHERE entry_id = ? ORDER BY id", (entry_id,)
    )
    entry["inflections"] = _rows(
        conn, "SELECT * FROM inflections WHERE entry_id = ? ORDER BY id", (entry_id,)
    )
    entry["exam_tags"] = _rows(
        conn, "SELECT * FROM exam_tags WHERE entry_id = ? ORDER BY exam", (entry_id,)
    )
    entry["senses"] = _rows(
        conn,
        "SELECT * FROM senses WHERE entry_id = ? ORDER BY part_of_speech, sense_number",
        (entry_id,),
    )
    for sense in entry["senses"]:
        sense_id = sense["id"]
        sense["translations"] = _rows(
            conn, "SELECT * FROM sense_translations WHERE sense_id = ? ORDER BY language, id",
            (sense_id,),
        )
        sense["semantic_relations"] = _rows(
            conn, "SELECT * FROM semantic_relations WHERE sense_id = ? ORDER BY id",
            (sense_id,),
        )
        sense["expressions"] = _rows(
            conn, "SELECT * FROM expressions WHERE sense_id = ? ORDER BY id",
            (sense_id,),
        )
        sense["examples"] = _rows(
            conn, "SELECT * FROM examples WHERE sense_id = ? ORDER BY id", (sense_id,)
        )
        for example in sense["examples"]:
            example["translations"] = _rows(
                conn,
                "SELECT * FROM example_translations WHERE example_id = ? ORDER BY language, id",
                (example["id"],),
            )
    return entry


def validate_database(conn: sqlite3.Connection) -> dict:
    """Run integrity checks and guard against mismatched upstream sense links."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    fk_errors = _rows(conn, "PRAGMA foreign_key_check")
    mismatched_links = conn.execute(
        "SELECT COUNT(*) FROM source_links sl "
        "JOIN senses s ON s.id = sl.sense_id "
        "WHERE sl.sense_id IS NOT NULL AND sl.entry_id != s.entry_id"
    ).fetchone()[0]
    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("entries", "senses", "sense_translations", "examples", "sources")
    }
    return {
        "ok": version == SCHEMA_VERSION and integrity == "ok"
        and not fk_errors and mismatched_links == 0,
        "schema_version": version,
        "integrity_check": integrity,
        "foreign_key_errors": len(fk_errors),
        "mismatched_source_links": mismatched_links,
        "counts": counts,
    }
