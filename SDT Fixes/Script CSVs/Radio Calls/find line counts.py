from __future__ import annotations

import csv
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SHA1_CSV = SCRIPT_DIR / "_csv_sha1s.csv"

MAX_WORKERS = max(4, os.cpu_count() or 4)

LINE_PREFIX_HEX_RE = re.compile(r"^(0x[0-9A-Fa-f]+),")


def normalize_rel_path(path: Path) -> str:
    return path.relative_to(SCRIPT_DIR).as_posix()


def find_csv_files() -> list[Path]:
    files: list[Path] = []

    for path in SCRIPT_DIR.rglob("*.csv"):
        if not path.is_file():
            continue

        if path.resolve() == SHA1_CSV.resolve():
            continue

        files.append(path)

    files.sort(key=lambda p: normalize_rel_path(p).lower())
    return files


def process_csv(path: Path) -> tuple[str, list[str], str | None]:
    rel_path = normalize_rel_path(path)
    matches: list[str] = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for raw_line in f:
                line = raw_line.rstrip("\r\n")
                match = LINE_PREFIX_HEX_RE.match(line)

                if match is None:
                    continue

                matches.append(match.group(1).lower())
    except Exception as exc:
        return rel_path, [], str(exc)

    return rel_path, matches, None


def format_array(values: list[str]) -> str:
    if not values:
        return "[]"

    unique = sorted(set(values), key=lambda value: int(value, 16))
    return "[" + ",".join(unique) + "]"


def atomic_write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)

        writer = csv.DictWriter(tmp_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for row in rows:
            writer.writerow(row)

    tmp_path.replace(path)


def main() -> int:
    if not SHA1_CSV.exists():
        print(f"Missing required file: {SHA1_CSV}")
        return 1

    csv_files = find_csv_files()

    results_by_path: dict[str, tuple[list[str], str | None]] = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(process_csv, path): path for path in csv_files}

        for future in as_completed(future_map):
            rel_path, matches, error = future.result()
            results_by_path[rel_path] = (matches, error)

    errors: list[tuple[str, str]] = []
    updated_rows: list[dict[str, str]] = []

    with SHA1_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            print(f"Invalid CSV header in: {SHA1_CSV}")
            return 1

        fieldnames = list(reader.fieldnames)

        if "hex_values" not in fieldnames:
            fieldnames.append("hex_values")

        for row in reader:
            row_dict = dict(row)

            rel_path = row_dict.get("relative_csv_path", "").strip()
            matches, error = results_by_path.get(rel_path, ([], None))

            if error is not None:
                errors.append((rel_path, error))
                row_dict["hex_values"] = "[]"
            else:
                row_dict["hex_values"] = format_array(matches)

            for field in fieldnames:
                row_dict.setdefault(field, "")

            updated_rows.append(row_dict)

    atomic_write_csv(SHA1_CSV, fieldnames, updated_rows)

    updated_count = len(updated_rows)
    matched_count = sum(
        1
        for row in updated_rows
        if row.get("hex_values", "[]") != "[]"
    )

    print(f"Updated: {SHA1_CSV}")
    print(f"Rows updated: {updated_count}")
    print(f"Rows with hex matches: {matched_count}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nFiles with errors:")
        for rel_path, error in sorted(errors, key=lambda item: item[0].lower()):
            print(f"{rel_path}: {error}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())