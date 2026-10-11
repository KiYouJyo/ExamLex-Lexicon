#!/usr/bin/env python3
"""Fetch selected words from FULL English Wiktionary via Kaikki per-word JSONL."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from import_kaikki import read_targets, normal_pos

BASE_URL = "https://kaikki.org/dictionary/English/meaning"
USER_AGENT = "ExamLex-Lexicon/0.2 (https://github.com/KiYouJyo/ExamLex-Lexicon)"
MAX_BYTES_PER_WORD = 24 * 1024 * 1024


def word_jsonl_url(word: str) -> str:
    """Construct the public Kaikki full-English per-headword JSONL link."""
    lemma = word.strip()
    if not lemma:
        raise ValueError("Empty lemma")
    low = lemma.casefold()
    return (
        f"{BASE_URL}/{quote(low[:1], safe='')}/"
        f"{quote(low[:2], safe='')}/{quote(lemma, safe='')}.jsonl"
    )


def _get_data(url: str, attempts: int = 3) -> bytes | None:
    """Missing page -> None; transient network errors -> retry, then fail."""
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=45) as stream:
                data = stream.read(MAX_BYTES_PER_WORD + 1)
            if len(data) > MAX_BYTES_PER_WORD:
                raise ValueError(f"Overlarge per-word JSONL: {url}")
            return data
        except HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code not in {408, 429, 500, 502, 503, 504} or attempt + 1 == attempts:
                raise
        except (URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Exhausted retries: {url}")


def _fetch_word(word: str, poses: set[str]) -> tuple[list[str], str | None]:
    data = _get_data(word_jsonl_url(word))
    if data is None:
        return [], "not_found"
    if not data.strip():
        return [], "empty"
    records = []
    for index, line in enumerate(data.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Bad JSONL for {word} at line {index}") from exc
        if not isinstance(record, dict) or record.get("lang_code") != "en":
            continue
        original = record.get("word")
        if not isinstance(original, str) or original.casefold() != word.casefold():
            continue
        try:
            pos = normal_pos(str(record.get("pos") or ""))
        except ValueError:
            continue
        if pos in poses:
            records.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return records, None if records else "no_requested_part_of_speech"


def download_selected(wordlist: Path, output: Path,
                      report: Path | None = None, workers: int = 4) -> dict:
    if not 1 <= workers <= 8:
        raise ValueError("workers must be 1..8")
    selected = read_targets(wordlist)
    items = {}
    errors = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(_fetch_word, word, pos): word
                for word, pos in selected.items()}
        for future in as_completed(jobs):
            word = jobs[future]
            try:
                lines, error = future.result()
            except Exception as exc:
                errors[word] = f"download_failed: {type(exc).__name__}: {exc}"
                continue
            items[word] = lines
            if error:
                errors[word] = error
    if any(e.startswith("download_failed:") for e in errors.values()):
        raise RuntimeError(f"Could not safely finish Kaikki downloads: {errors}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        for word in sorted(selected):
            for record in items.get(word, []):
                stream.write(record + "\n")
    result = {
        "source": "Full English Wiktionary (Kaikki per-word JSONL)",
        "selected_unique_words": len(selected),
        "downloaded_matching_words": sum(bool(records) for records in items.values()),
        "downloaded_records": sum(len(records) for records in items.values()),
        "missing_or_no_matching_pos": errors,
        "output": str(output),
    }
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wordlist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(
        download_selected(args.wordlist, args.output, args.report, args.workers),
        ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
