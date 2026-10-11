# ExamLex Lexicon

**ExamLex Lexicon** is the standalone, offline-first lexical database for [ExamLex](https://github.com/KiYouJyo/ExamLex).

This repository contains the **database schema and reproducible build tools**, not a redistribution of third-party dictionaries. Its goal is to progressively combine English definitions, Chinese and Japanese glosses, pronunciation, inflections, semantic relations, grammar patterns, collocations, examples, CEFR levels, and exam-oriented tags.

## Principles

- **Sense-first:** separate a word, its parts of speech, and its meanings. Translations, examples, and collocations attach to the appropriate sense.
- **Incremental:** incomplete entries are expected. Missing data stays `NULL` / absent, rather than being invented.
- **Traceable:** imported content links to a source and can be revised without erasing the original attribution.
- **Simple CEFR:** one optional A1–C2 label per entry, sourced from an authorized reference or editorial decision. No complicated sense-level CEFR model.
- **Offline-first:** SQLite is the deliverable format, independent of the Windows UI.
- **License-aware:** each upstream dataset has its own license; the program license does not automatically cover dictionary content.

## Quick start

Requires Python 3.11+; no third-party runtime packages.

```bash
# From the repository root
PYTHONPATH=src python -m examlex_lexicon --db build/examlex.db init
PYTHONPATH=src python -m examlex_lexicon --db build/examlex.db seed-demo
PYTHONPATH=src python -m examlex_lexicon --db build/examlex.db lookup address
PYTHONPATH=src python -m examlex_lexicon --db build/examlex.db validate
PYTHONPATH=src python -m unittest discover -s tests -v
```

PowerShell equivalents:

```powershell
$env:PYTHONPATH = "src"
python -m examlex_lexicon --db build/examlex.db init
python -m examlex_lexicon --db build/examlex.db seed-demo
python -m examlex_lexicon --db build/examlex.db lookup address
python -m examlex_lexicon --db build/examlex.db validate
python -m unittest discover -s tests -v
```

The `seed-demo` command adds **illustrative, locally authored data only**. It is not a licensed dictionary import, a vocabulary frequency claim, or an authoritative CEFR rating. Do not run it when building public production datasets.

## Repository structure

```text
schema/                    SQLite schema (v1)
src/examlex_lexicon/        Standard-library CLI, database helpers and demo
tests/                     SQLite and command-line tests
docs/DATA_MODEL.md         Table layout and merge design
SOURCES.md                 Upstream licensing and provenance policy
.github/workflows/         Automated validation
build/                     Generated databases (gitignored)
```

## Current scope (foundation v0.1)

The schema and CLI are operational for empty databases and demo records. **Kaikki, ECDICT, EJDict, WordNet, EVP and Oxford importers are not implemented yet**; actual vocabulary ingestion will follow source-license review and sample-level sense-matching tests.

See [the data model](docs/DATA_MODEL.md) and [source policy](SOURCES.md).

## Licensing

Source code and project-created database tooling may be licensed independently from imported lexical content. Upstream data retains its applicable terms, including attribution and share-alike obligations where relevant. Refer to [SOURCES.md](SOURCES.md). No third-party dictionary dump is included in this repository.
