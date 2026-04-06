from __future__ import annotations

import csv
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ORIGINAL_ROOT = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\original_subtitles")
MERGED_DIR = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\merged_subtitles")

MAX_WORKERS = max(4, os.cpu_count() or 4)

META_COLUMNS = [
    "__relative_csv_path",
    "__source_row_number",
]


def get_pass_folders(root: Path) -> list[Path]:
    return sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name.lower())


def get_csvs(pass_folder: Path) -> list[Path]:
    return sorted(pass_folder.rglob("*.csv"), key=lambda p: p.relative_to(pass_folder).as_posix().lower())


def read_csv(path: Path, pass_folder: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            return [], []

        fields = list(reader.fieldnames)
        rows = []

        idx = 1
        for row in reader:
            idx += 1

            out = {
                "__relative_csv_path": path.relative_to(pass_folder).as_posix(),
                "__source_row_number": str(idx),
            }

            for field in fields:
                val = row.get(field, "")
                out[field] = "" if val is None else str(val)

            rows.append(out)

        return fields, rows


def merge_pass(pass_folder: Path):
    csvs = get_csvs(pass_folder)
    if not csvs:
        return pass_folder.name, 0, 0

    all_rows = []
    all_fields = []

    for path in csvs:
        fields, rows = read_csv(path, pass_folder)

        for f in fields:
            if f not in all_fields:
                all_fields.append(f)

        all_rows.extend(rows)

    columns = META_COLUMNS + all_fields

    base_path = MERGED_DIR / f"{pass_folder.name}.csv"
    corrected_path = MERGED_DIR / f"{pass_folder.name}_corrected.csv"

    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    with base_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=columns,
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for row in all_rows:
            writer.writerow({c: row.get(c, "") for c in columns})

    shutil.copy2(base_path, corrected_path)

    return pass_folder.name, len(csvs), len(all_rows)


def main():
    passes = get_pass_folders(ORIGINAL_ROOT)
    if not passes:
        print("No passes found.")
        return

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(passes))) as exe:
        futures = {exe.submit(merge_pass, p): p for p in passes}

        done = 0
        total = len(futures)

        for fut in as_completed(futures):
            done += 1
            p = futures[fut]

            try:
                name, count, rows = fut.result()
                print(f"[{done}/{total}] {name}: {count} csvs, {rows} rows")
            except Exception as e:
                print(f"[{done}/{total}] {p.name}: ERROR {e}")


if __name__ == "__main__":
    main()