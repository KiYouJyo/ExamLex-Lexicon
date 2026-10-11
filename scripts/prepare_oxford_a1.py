#!/usr/bin/env python3
"""Convert a user's locally saved Oxford-3000-by-CEFR PDF into an A1 CSV.

The script does not download or redistribute Oxford content. Use the resulting
CSV locally and do not commit it to this public repository.

Install optional dependency: python -m pip install PyMuPDF
"""
from __future__ import annotations
import argparse
import csv
import re
from pathlib import Path

ALIASES = {
    "n.": "noun", "v.": "verb", "adj.": "adj", "adv.": "adv",
    "prep.": "prep", "pron.": "pron", "det.": "det", "conj.": "conj",
    "exclam.": "intj", "number": "num",
    "modal v.": "verb", "auxiliary v.": "verb", "indefinite article": "article",
}
PATTERN = r"indefinite article|auxiliary v\.|modal v\.|exclam\.|number|pron\.|prep\.|conj\.|det\.|adj\.|adv\.|n\.|v\."
POS_PATTERN = re.compile(PATTERN)
FIRST_POS = re.compile(r"\s(?:" + PATTERN + r")")

def parse_a1_lines(lines: list[str]) -> list[tuple[str, str]]:
    seen = set()
    results = []
    inside = False
    found_start = found_end = False
    for raw in lines:
        line = " ".join(raw.replace("\u00a0", " ").split())
        if line == "A1":
            inside = found_start = True
            continue
        if inside and line == "A2":
            found_end = True
            break
        if not inside or not line or "Oxford University Press" in line:
            continue
        if "Oxford 3000" in line or re.fullmatch(r"\d+\s*/\s*\d+", line):
            continue
        match = FIRST_POS.search(line)
        if match is None:
            continue
        word = line[:match.start()].strip()
        grammar = line[match.start():].strip()
        word = re.sub(r"\s*\([^)]*\)\s*$", "", word)
        word = re.sub(r"(?<=[A-Za-z])[0-9¹²³⁴⁵⁶⁷⁸⁹⁰]+$", "", word)
        words = [s.strip() for s in word.split(",")] if word == "a, an" else [word]
        for lemma in words:
            if not lemma or len(lemma) > 100:
                continue
            for match in POS_PATTERN.finditer(grammar):
                item = (lemma, ALIASES[match.group(0)])
                if (item[0].casefold(), item[1]) not in seen:
                    seen.add((item[0].casefold(), item[1]))
                    results.append(item)
    if not (found_start and found_end):
        raise ValueError("Missing A1 or A2 heading. Use Oxford 3000 *by CEFR level* PDF.")
    if len(results) < 5:
        raise ValueError("Too few parsed A1 words; inspect your PDF text extraction.")
    return results

def extract_pdf_lines(path: Path) -> list[str]:
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF: python -m pip install PyMuPDF") from exc
    with pymupdf.open(path) as doc:
        text = "\n".join(page.get_text("text", sort=True) for page in doc)
    return text.splitlines()

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdf", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("build/oxford_a1.csv"))
    args = p.parse_args()
    rows = parse_a1_lines(extract_pdf_lines(args.pdf))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["word", "pos", "cefr_level"])
        w.writerows((word, pos, "A1") for word, pos in rows)
    print(f"Wrote {len(rows)} A1 word-POS pairs to {args.output}")
    print("Keep the full Oxford-derived selection local; do not republish without permission.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
