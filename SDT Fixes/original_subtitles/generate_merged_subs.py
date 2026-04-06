from __future__ import annotations

import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ORIGINAL_ROOT = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\original_subtitles")
MERGED_OUTPUT_DIR = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\merged_subtitles_original")

MAX_WORKERS = max(4, os.cpu_count() or 4)

META_COLUMNS = [
    "__relative_csv_path",
    "__source_row_number",
]


def get_pass_folders(root: Path) -> list[Path]:
    return sorted([path for path in root.iterdir() if path.is_dir()], key=lambda p: p.name.lower())


def get_csv_files(pass_folder: Path) -> list[Path]:
    return sorted(pass_folder.rglob("*.csv"), key=lambda p: p.relative_to(pass_folder).as_posix().lower())


def read_csv_rows(csv_path: Path, pass_folder: Path) -> tuple[list[str], list[dict[str, str]]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            return [], []

        fieldnames = list(reader.fieldnames)
        rows: list[dict[str, str]] = []

        source_row_number = 1

        for row in reader:
            source_row_number += 1

            merged_row: dict[str, str] = {
                "__relative_csv_path": csv_path.relative_to(pass_folder).as_posix(),
                "__source_row_number": str(source_row_number),
            }

            for field in fieldnames:
                value = row.get(field, "")

                if value is None:
                    value = ""

                merged_row[field] = str(value)

            rows.append(merged_row)

        return fieldnames, rows


def merge_pass(pass_folder: Path) -> tuple[str, int, int]:
    csv_files = get_csv_files(pass_folder)

    if not csv_files:
        return pass_folder.name, 0, 0

    merged_rows: list[dict[str, str]] = []
    discovered_columns: list[str] = []

    for csv_path in csv_files:
        fieldnames, rows = read_csv_rows(csv_path, pass_folder)

        for field in fieldnames:
            if field not in discovered_columns:
                discovered_columns.append(field)

        merged_rows.extend(rows)

    output_columns = META_COLUMNS + discovered_columns

    output_path = MERGED_OUTPUT_DIR / f"{pass_folder.name}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=output_columns,
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()

        for row in merged_rows:
            output_row = {column: row.get(column, "") for column in output_columns}
            writer.writerow(output_row)

    return pass_folder.name, len(csv_files), len(merged_rows)


def main() -> None:
    if not ORIGINAL_ROOT.is_dir():
        raise SystemExit(f"Missing folder: {ORIGINAL_ROOT}")

    MERGED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pass_folders = get_pass_folders(ORIGINAL_ROOT)

    if not pass_folders:
        print("No pass folders found.")
        return

    results: list[tuple[str, int, int]] = []

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(pass_folders))) as executor:
        futures = {
            executor.submit(merge_pass, pass_folder): pass_folder
            for pass_folder in pass_folders
        }

        completed = 0
        total = len(futures)

        for future in as_completed(futures):
            pass_folder = futures[future]
            completed += 1

            try:
                pass_name, csv_count, row_count = future.result()
                results.append((pass_name, csv_count, row_count))
                print(f"[{completed}/{total}] {pass_name}: {csv_count} csvs, {row_count} rows")
            except Exception as e:
                print(f"[{completed}/{total}] {pass_folder.name}: ERROR: {e}")

    results.sort(key=lambda item: item[0].lower())

    print()
    for pass_name, csv_count, row_count in results:
        print(f"{pass_name}: {csv_count} csvs, {row_count} rows")

    print()
    print(f"Output folder: {MERGED_OUTPUT_DIR}")


if __name__ == "__main__":
    main()