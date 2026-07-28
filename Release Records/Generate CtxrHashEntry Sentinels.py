from __future__ import annotations

import csv
import os
import re
import sys
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


INDENT = "    "


def clean_path(value: str) -> str:
    value = value.strip().strip('"').strip("'")

    value = "".join(
        character
        for character in value
        if unicodedata.category(character) not in {"Cf", "Cc"}
    )

    return value.replace("\\", "/").rstrip("/").casefold()


def display_path(value: str) -> str:
    value = value.strip().strip('"').strip("'")

    value = "".join(
        character
        for character in value
        if unicodedata.category(character) not in {"Cf", "Cc"}
    )

    return value.replace("\\", "/").rstrip("/")


def paths_match(input_path: str, csv_path: str) -> bool:
    input_path = clean_path(input_path)
    csv_path = clean_path(csv_path)

    return input_path == csv_path or csv_path.endswith("/" + input_path)


def sanitize_identifier(value: str) -> str:
    identifier = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")

    if not identifier:
        identifier = "Unknown"

    if identifier[0].isdigit():
        identifier = "_" + identifier

    return identifier


def format_version_identifier(version: str) -> str:
    return sanitize_identifier(version.strip().lstrip("vV"))


def detect_fix_variant(source_names: list[str]) -> str:
    combined = " ".join(format_source_name(name) for name in source_names)

    if re.search(r"\b4x\b", combined, re.IGNORECASE):
        return "4x"

    if re.search(r"\b2x\b", combined, re.IGNORECASE):
        return "2x"

    if re.search(r"\bbase\b", combined, re.IGNORECASE):
        return "Base"

    return sanitize_identifier(Path(source_names[0]).stem)


def make_table_name(source_names: list[str], old_version: str, new_version: str) -> str:
    variant = detect_fix_variant(source_names)
    old_id = format_version_identifier(old_version)
    new_id = format_version_identifier(new_version)
    return f"kRemoved_Fixes_{variant}_v{old_id}_to_v{new_id}"


def get_input_paths() -> list[str]:
    if len(sys.argv) > 1:
        argument = Path(sys.argv[1])

        if len(sys.argv) == 2 and argument.is_file():
            return [
                line
                for line in argument.read_text(encoding="utf-8-sig").splitlines()
                if clean_path(line)
            ]

        return [argument for argument in sys.argv[1:] if clean_path(argument)]

    print("Paste file paths, one per line.")
    print("Press Enter on a blank line when finished.\n")

    paths: list[str] = []

    while True:
        line = input()

        if not line.strip():
            break

        paths.append(line)

    return paths


def read_csv_entries(csv_path: Path) -> tuple[str, list[tuple[str, str]], str | None]:
    entries: list[tuple[str, str]] = []

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                return csv_path.name, entries, "CSV has no header"

            normalized_headers = {
                clean_path(header): header
                for header in reader.fieldnames
                if header
            }

            full_path_header = normalized_headers.get("full_path")
            sha1_header = normalized_headers.get("sha1")

            if not full_path_header or not sha1_header:
                return csv_path.name, entries, "missing full_path or sha1 column"

            for row in reader:
                full_path = row.get(full_path_header, "")
                sha1 = row.get(sha1_header, "").strip().lower()

                if full_path and sha1:
                    entries.append((full_path, sha1))

        return csv_path.name, entries, None

    except (OSError, csv.Error, UnicodeError) as error:
        return csv_path.name, entries, str(error)


def print_progress(current: int, total: int, width: int = 40) -> None:
    if total <= 0:
        return

    filled = int(width * current / total)
    bar = "#" * filled + "-" * (width - filled)
    percent = current * 100.0 / total

    print(
        f"\rReading CSV files: [{bar}] {current}/{total} {percent:6.2f}%",
        end="",
        flush=True,
    )

    if current == total:
        print()


def load_all_entries(folder: Path) -> dict[str, list[tuple[str, str]]]:
    csv_paths = sorted(folder.glob("*.csv"))

    if not csv_paths:
        return {}

    entries_by_csv: dict[str, list[tuple[str, str]]] = {}
    worker_count = min(len(csv_paths), max(1, os.cpu_count() or 1))

    print(f"Scanning {len(csv_paths)} CSV file(s) with {worker_count} worker thread(s)...")

    completed = 0

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(read_csv_entries, csv_path): csv_path
            for csv_path in csv_paths
        }

        for future in as_completed(futures):
            csv_name, entries, error = future.result()

            if error:
                print(f"\nSkipping {csv_name}: {error}")
            else:
                entries_by_csv[csv_name] = entries

            completed += 1
            print_progress(completed, len(csv_paths))

    return entries_by_csv


def collect_matches(
    input_paths: list[str],
    entries_by_csv: dict[str, list[tuple[str, str]]],
) -> tuple[
    dict[str, tuple[tuple[str, str], ...]],
    dict[str, list[str]],
]:
    matches_by_csv: dict[str, tuple[tuple[str, str], ...]] = {}
    missing_by_csv: dict[str, list[str]] = {}

    for csv_name, entries in entries_by_csv.items():
        matches: list[tuple[str, str]] = []
        missing: list[str] = []

        for input_path in input_paths:
            matched_sha1: str | None = None

            for csv_path, sha1 in entries:
                if paths_match(input_path, csv_path):
                    matched_sha1 = sha1
                    break

            if matched_sha1 is None:
                missing.append(display_path(input_path))
                continue

            filename = Path(display_path(input_path)).stem
            entry = (filename, matched_sha1)

            if entry not in matches:
                matches.append(entry)

        if matches:
            matches_by_csv[csv_name] = tuple(matches)

        if missing:
            missing_by_csv[csv_name] = missing

    return matches_by_csv, missing_by_csv


def format_source_name(csv_name: str) -> str:
    return Path(csv_name).stem.replace("_", " ")


def get_parent_directories(input_paths: list[str]) -> list[str]:
    parent_directories: list[str] = []
    seen: set[str] = set()

    for input_path in input_paths:
        parent = str(Path(display_path(input_path)).parent).replace("\\", "/")
        key = clean_path(parent)

        if key in seen:
            continue

        seen.add(key)
        parent_directories.append(parent)

    return parent_directories


def format_cpp_table(
    comment_paths: list[str],
    table_name: str,
    entries: tuple[tuple[str, str], ...],
    source_names: list[str] | None = None,
) -> str:
    if len(comment_paths) == 1:
        comments = [f"/// all files in {comment_paths[0]}/"]
    else:
        comments = ["/// all files in:"]
        comments.extend(f"/// {path}/" for path in comment_paths)

    if source_names:
        comments[-1] += f" ({', '.join(format_source_name(name) for name in source_names)})"

    lines = [
        *comments,
        f"constexpr CtxrHashEntry {table_name}[] =",
        "{",
    ]

    for filename, sha1 in entries:
        lines.append(f'{INDENT}{{ "{filename}", "{sha1}" }},')

    lines.append("};")
    return "\n".join(lines)


def main() -> None:
    script_folder = Path(__file__).resolve().parent
    input_paths = get_input_paths()

    if not input_paths:
        print("No file paths entered.")
        input("\nPress Enter to exit...")
        return

    old_version = input("\nTable name - from version: ").strip()
    new_version = input("Table name - to version: ").strip()

    if not old_version or not new_version:
        print("Both version numbers are required for the generated table name.")
        input("\nPress Enter to exit...")
        return

    comment_paths = get_parent_directories(input_paths)
    entries_by_csv = load_all_entries(script_folder)

    if not entries_by_csv:
        print("No usable entries were found in the CSV files beside the script.")
        input("\nPress Enter to exit...")
        return

    matches_by_csv, missing_by_csv = collect_matches(input_paths, entries_by_csv)

    if not matches_by_csv:
        print("None of the CSV files contained any of the pasted paths.")
        input("\nPress Enter to exit...")
        return

    grouped_results: dict[tuple[tuple[str, str], ...], list[str]] = defaultdict(list)

    for csv_name, matches in matches_by_csv.items():
        grouped_results[matches].append(csv_name)

    print("\nC++ output:\n")

    if len(grouped_results) == 1:
        entries, source_names = next(iter(grouped_results.items()))
        table_name = make_table_name(source_names, old_version, new_version)
        print(format_cpp_table(comment_paths, table_name, entries, sorted(source_names)))
        print(f"\nAll {len(source_names)} CSV match(es) with at least one entry were 1:1 identical.")
    else:
        sorted_groups = sorted(
            grouped_results.items(),
            key=lambda item: min(item[1]).casefold(),
        )

        used_names: dict[str, int] = defaultdict(int)

        for entries, source_names in sorted_groups:
            group_table_name = make_table_name(source_names, old_version, new_version)
            used_names[group_table_name] += 1

            if used_names[group_table_name] > 1:
                group_table_name += f"_{used_names[group_table_name]}"

            print(format_cpp_table(comment_paths, group_table_name, entries, sorted(source_names)))
            print()

        print(
            f"Found {len(grouped_results)} distinct file/hash sets across "
            f"{len(matches_by_csv)} CSV match(es) containing at least one entry."
        )

    no_match_count = len(entries_by_csv) - len(matches_by_csv)

    if no_match_count:
        print(f"Ignored {no_match_count} CSV file(s) that contained none of the listed paths.")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()