# v0.2 - A1 local import workflow

The public repository contains a small pilot list, importer, tests, and tooling.
The pilot now uses **full English Wiktionary**. Older Simple Wiktionary releases remain immutable historical builds.
It deliberately DOES NOT contain the full proprietary Oxford 3000 A1 selection.
To build the full A1 selection locally, use your own copy of Oxford's official
"Oxford 3000 by CEFR level" PDF from:

https://www.oxfordlearnersdictionaries.com/external/pdf/wordlists/oxford-3000-5000/The_Oxford_3000_by_CEFR_level.pdf

Oxford reference data is not the source of the English definitions: those come
from Kaikki / Wiktionary (Wiktextract).

## Windows PowerShell steps

1. Download the Oxford PDF into the repository directory yourself. Check its
   current licensing / usage conditions before any republication.
2. Prepare a LOCAL Oxford A1 word/POS CSV (the generated file is gitignored):

    python -m pip install PyMuPDF
    python scripts/prepare_oxford_a1.py --pdf "The_Oxford_3000_by_CEFR_level.pdf" --output build/oxford_a1.csv

3. Download only the selected words from FULL English Wiktionary via Kaikki,
   without fetching the 2.8 GB all-language raw dump:

    $env:PYTHONPATH = "src"
    python scripts/fetch_kaikki_english_words.py --wordlist build/oxford_a1.csv --output build/oxford-a1-english.jsonl --report build/download-report.json

   Inspect download-report.json for missing word pages. This fetch uses
   Kaikki's public English word-level JSONL files (postprocessed output).

4. Import the downloaded English JSONL and check every selected part of speech:

    python scripts/import_kaikki.py --wordlist build/oxford_a1.csv --input build/oxford-a1-english.jsonl --source-kind en --cefr-source "Oxford 3000 A1 (locally checked)" --db build/oxford-a1.db --report build/oxford-a1-report.json
    python -m examlex_lexicon --db build/oxford-a1.db validate
    python -m examlex_lexicon --db build/oxford-a1.db lookup about

5. For fuller coverage, download Kaikki's much larger English Wiktionary JSONL
   or JSONL.gz export from https://kaikki.org/dictionary/rawdata.html and change
   --source-kind from simple to en. Full raw export may take several GB of disk
   and time. Importer reads it line by line.

## Data policy and practical notes

- The CSV must contain word,pos,cefr_level headers. All imported targets must
  be A1. Multiple POS rows per word are supported.
- Oxford's A1 can be POS-specific: address = noun A1, verb B2. The importer
  excludes POS combinations missing from the target list.
- Only the simple entry-level CEFR A1 label is stored, as requested. Imported
  Wiktionary senses within an included POS can have higher usage complexity.
- Kaikki supplies source English definitions, pronunciation, inflections,
  some example sentences and semantic relations. No synthetic bilingual data
  or invented exam-frequency tags are inserted.
- Empty Chinese/Japanese translation, collocation and valency fields remain
  empty for later stages. Published versions must review dataset licenses.
- Re-running against the same source deduplicates existing source sense links.
- The import report includes `missing_word_pos`: matching a word is **not** enough if its selected noun, verb, adjective or adverb POS is missing.
- Eligible source senses are preserved without an arbitrary 10-sense ceiling; similar English explanations are not automatically merged.
- After updating the PDF converter or source format, manually inspect local
  build/oxford_a1.csv for missing multiword phrases, pronunciation variants,
  POS mismatches, and PDF column extraction problems.
- The Actions workflow "Build A1 pilot SQLite" publishes a downloadable full-English-Wiktionary pilot
  SQLite artifact with source attribution and a JSON import coverage report.
  This pilot is NOT a complete Oxford A1 export.

## Test

    $env:PYTHONPATH = "src"
    python -m unittest discover -s tests -v
