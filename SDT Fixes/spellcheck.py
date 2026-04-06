from __future__ import annotations

import csv
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Iterable

try:
    from spellchecker import SpellChecker
except ImportError:
    print("Missing dependency: pyspellchecker")
    print("Install it with: pip install pyspellchecker")
    sys.exit(1)


ROOT_DIR = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\original_subtitles")
OUTPUT_CSV = ROOT_DIR / "_eng_spellcheck_results.csv"
CUSTOM_WORDS_TXT = ROOT_DIR / "_eng_spellcheck_custom_words.txt"

MAX_WORKERS = max(4, os.cpu_count() or 4)

TEXT_COLUMN_EXCLUSIONS = {
    "Start Time",
    "End Time",
    "Lang ID",
}

WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
NUMBER_RE = re.compile(r"^\d+$")


spellchecker_lock = Lock()
custom_words_lock = Lock()


def load_custom_words(path: Path) -> set[str]:
    if not path.is_file():
        return set()

    words: set[str] = set()

    with path.open("r", encoding="utf-8", newline="") as f:
        for line in f:
            word = line.strip().lower()

            if not word or word.startswith("#"):
                continue

            words.add(word)

    return words


def build_spellchecker(custom_words: set[str]) -> SpellChecker:
    checker = SpellChecker(language="en")

    if custom_words:
        checker.word_frequency.load_words(custom_words)

    return checker


def get_csv_files(root_dir: Path) -> list[Path]:
    return sorted(root_dir.rglob("*.csv"))


def is_text_column(column_name: str) -> bool:
    return column_name not in TEXT_COLUMN_EXCLUSIONS


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text)


def clean_token_for_lookup(token: str) -> str:
    return token.replace("’", "'").strip("'").lower()


def should_skip_token(token: str, custom_words: set[str]) -> bool:
    normalized = clean_token_for_lookup(token)

    if not normalized:
        return True

    if NUMBER_RE.fullmatch(normalized):
        return True

    if len(normalized) <= 1:
        return True

    if normalized in custom_words:
        return True

    return False


def get_suggestion(checker: SpellChecker, token: str) -> str:
    normalized = clean_token_for_lookup(token)

    with spellchecker_lock:
        correction = checker.correction(normalized)

    if not correction or correction == normalized:
        return ""

    return correction


def process_csv(path: Path, root_dir: Path, checker: SpellChecker, custom_words: set[str]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                return results

            row_number = 1

            for row in reader:
                row_number += 1

                if (row.get("Lang ID") or "").strip() != "[ENG]":
                    continue

                for column_name, value in row.items():
                    if not is_text_column(column_name):
                        continue

                    if value is None:
                        continue

                    value = value.strip()

                    if not value:
                        continue

                    for token in tokenize(value):
                        if should_skip_token(token, custom_words):
                            continue

                        normalized = clean_token_for_lookup(token)

                        with spellchecker_lock:
                            is_unknown = normalized in checker.unknown([normalized])

                        if not is_unknown:
                            continue

                        suggestion = get_suggestion(checker, token)

                        results.append(
                            {
                                "relative_csv_path": path.relative_to(root_dir).as_posix(),
                                "row_number": str(row_number),
                                "column_name": column_name,
                                "token": token,
                                "suggestion": suggestion,
                                "full_text": value,
                            }
                        )

    except Exception as e:
        results.append(
            {
                "relative_csv_path": path.relative_to(root_dir).as_posix(),
                "row_number": "",
                "column_name": "",
                "token": "",
                "suggestion": "",
                "full_text": f"[ERROR] {e}",
            }
        )

    return results


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "relative_csv_path",
        "row_number",
        "column_name",
        "token",
        "suggestion",
        "full_text",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not ROOT_DIR.is_dir():
        print(f"Root directory does not exist: {ROOT_DIR}")
        sys.exit(1)

    custom_words = load_custom_words(CUSTOM_WORDS_TXT)
    checker = build_spellchecker(custom_words)

    csv_files = get_csv_files(ROOT_DIR)

    if not csv_files:
        print("No CSV files found.")
        sys.exit(0)

    all_results: list[dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_csv, path, ROOT_DIR, checker, custom_words): path
            for path in csv_files
        }

        completed = 0
        total = len(futures)

        for future in as_completed(futures):
            path = futures[future]
            completed += 1

            try:
                rows = future.result()
                all_results.extend(rows)
            except Exception as e:
                all_results.append(
                    {
                        "relative_csv_path": path.relative_to(ROOT_DIR).as_posix(),
                        "row_number": "",
                        "column_name": "",
                        "token": "",
                        "suggestion": "",
                        "full_text": f"[ERROR] {e}",
                    }
                )

            print(f"[{completed}/{total}] {path.relative_to(ROOT_DIR).as_posix()}")

    all_results.sort(
        key=lambda row: (
            row["relative_csv_path"].lower(),
            int(row["row_number"]) if row["row_number"].isdigit() else 0,
            row["column_name"].lower(),
            row["token"].lower(),
        )
    )

    write_results(OUTPUT_CSV, all_results)

    print()
    print(f"Scanned CSV files: {len(csv_files)}")
    print(f"Potential issues found: {len(all_results)}")
    print(f"Output: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()