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

Requires Python 3.11+; base CLI/importer has no third-party runtime packages. The optional PDF converter requires PyMuPDF.

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
scripts/                   Oxford-local and Kaikki import tools
data/samples/              Small pilot word/POS filter
src/examlex_lexicon/        Standard-library CLI, database helpers and demo
tests/                     SQLite and command-line tests
docs/DATA_MODEL.md         Table layout and merge design
docs/A1_IMPORT.md          A1 local conversion and import instructions
SOURCES.md                 Upstream licensing and provenance policy
.github/workflows/         Automated validation
build/                     Generated databases (gitignored)
```

## A1 import (v0.2)

The first **real lexical-data import** is implemented. The importer reads Kaikki/Wiktextract English JSONL or JSONL.gz and filters it by a local **Oxford A1 word + part of speech** CSV. It adds English definitions, IPA, inflections, meaning-level relations, and eligible usage examples; missing Chinese/Japanese meanings remain empty. The pilot source is now full English Wiktionary via Kaikki, not Simple Wiktionary.

- [A1 import instructions for Windows and other platforms](docs/A1_IMPORT.md)
- [Oxford PDF to private A1 CSV converter](scripts/prepare_oxford_a1.py) (requires optional PyMuPDF dependency)
- [Streaming Kaikki JSONL importer](scripts/import_kaikki.py)
- [Full English Wiktionary per-word downloader](scripts/fetch_kaikki_english_words.py)
- [Small 120-word development pilot selection](data/samples/a1_pilot.csv) (NOT a full Oxford A1 list)
- [Pilot SQLite workflow and downloadable artifact](https://github.com/KiYouJyo/ExamLex-Lexicon/actions/workflows/a1-pilot.yml)

Example **pilot-only** workflow using **full English Wiktionary** per-word JSONL (no multi-GB download):

```powershell
$env:PYTHONPATH = "src"
python scripts/fetch_kaikki_english_words.py --wordlist data/samples/a1_pilot.csv --output build/a1-english.jsonl --report build/fetch-report.json
python scripts/import_kaikki.py --wordlist data/samples/a1_pilot.csv --input build/a1-english.jsonl --source-kind en --cefr-source "Manual A1 pilot selection (Oxford-referenced)" --db build/a1-pilot.db --report build/a1-report.json
python -m examlex_lexicon --db build/a1-pilot.db validate
```

Use the PDF converter and locally held complete Oxford A1 PDF to generate a **private** full A1 selection; that complete wordlist is intentionally not redistributed here.

Kaikki importer and full-English-Wiktionary downloader are implemented. The previous Simple Wiktionary v0.1 release is preserved; the corrected v0.2 series replaces it for new installs. Reports separately check words **and** word/POS combinations. ECDICT, EJDict and WordNet integrations are planned for later stages. See [data model](docs/DATA_MODEL.md) and [source policy](SOURCES.md).

## Licensing

Source code and project-created database tooling may be licensed independently from imported lexical content. Upstream data retains its applicable terms, including attribution and share-alike obligations where relevant. Refer to [SOURCES.md](SOURCES.md). No third-party dictionary dump is included in this repository.
