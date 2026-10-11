"""Command-line tools for creating and inspecting a local ExamLex SQLite DB."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .db import connect_database, initialize_database, lookup_word, validate_database
from .demo import seed_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ExamLex Lexicon database tools")
    parser.add_argument(
        "--db", type=Path, default=Path("build/examlex.db"),
        help="Path to SQLite file (default: build/examlex.db)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize an empty database")
    commands.add_parser("seed-demo", help="Add a hand-authored illustrative entry")
    lookup = commands.add_parser("lookup", help="Look up an English headword")
    lookup.add_argument("word", help="English word to look up")
    commands.add_parser("validate", help="Check schema, foreign keys and integrity")
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            initialize_database(args.db)
            print(f"Initialized schema v1: {args.db}")
            return 0
        with connect_database(args.db) as conn:
            if args.command == "seed-demo":
                if conn.execute("PRAGMA user_version").fetchone()[0] != 1:
                    raise ValueError("Uninitialized database; run 'init' first.")
                added = seed_demo(conn)
                print("Demo inserted." if added else "Demo skipped: word already exists.")
                return 0
            if args.command == "lookup":
                entry = lookup_word(conn, args.word)
                if entry is None:
                    print(f"Not found: {args.word}", file=sys.stderr)
                    return 1
                print(json.dumps(entry, ensure_ascii=False, indent=2))
                return 0
            if args.command == "validate":
                report = validate_database(conn)
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 0 if report["ok"] else 1
    except (FileNotFoundError, ValueError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
