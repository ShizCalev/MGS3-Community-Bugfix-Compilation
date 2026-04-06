from __future__ import annotations

import csv
import hashlib
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


SCRIPT = Path(
    r"C:\Development\Git\Afevis-MGS2-Bugfix-Compilation\external\SDT-Tools\0000.SDT_extractor.py"
)
SOURCE_ROOT = Path(r"G:\Steam\steamapps\common\MGS3")
THREADS = os.cpu_count() or 8
DEST_ROOT = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Script CSVs\Cutscenes")
SHA1_CSV = DEST_ROOT / "_csv_sha1s.csv"
SHA1_BUFFER_SIZE = 8 * 1024 * 1024


def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(SHA1_BUFFER_SIZE), b""):
            h.update(chunk)

    return h.hexdigest()


def process_file(sdt_path: Path, source_root: Path) -> str:
    rel_path = sdt_path.relative_to(source_root)
    csv_path = DEST_ROOT / rel_path.with_suffix(".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            ["python", str(SCRIPT), str(sdt_path), str(csv_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            return f"[OK] {rel_path}"

        stderr = result.stderr.strip()
        if stderr:
            return f"[ERR] {rel_path}\n{stderr}"
        return f"[ERR] {rel_path}"
    except Exception as e:
        return f"[FAIL] {rel_path}: {e}"


def main() -> None:
    if not SOURCE_ROOT.is_dir():
        print(f"Source root does not exist: {SOURCE_ROOT}")
        return

    sdt_files = list(SOURCE_ROOT.rglob("*.sdt"))

    if not sdt_files:
        print(f"No .sdt files found recursively under: {SOURCE_ROOT}")
        return

    print(f"Found {len(sdt_files)} .sdt files. Processing with {THREADS} threads...\n")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(process_file, f, SOURCE_ROOT): f for f in sdt_files}
        for fut in as_completed(futures):
            print(fut.result())

    sha1_rows: list[tuple[str, str, str]] = []

    for sdt_path in sdt_files:
        rel_path = sdt_path.relative_to(SOURCE_ROOT)
        csv_path = DEST_ROOT / rel_path.with_suffix(".csv")

        if not csv_path.is_file():
            continue

        csv_rel_path = csv_path.relative_to(DEST_ROOT).as_posix()
        csv_sha1 = sha1_of_file(csv_path)
        sdt_sha1 = sha1_of_file(sdt_path)
        sha1_rows.append((csv_rel_path, csv_sha1, sdt_sha1))

    sha1_rows.sort(key=lambda row: row[0].lower())

    SHA1_CSV.parent.mkdir(parents=True, exist_ok=True)

    with SHA1_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["relative_csv_path", "csv_sha1", "sdt_sha1"])
        writer.writerows(sha1_rows)

    print(f"\nWrote SHA1 CSV: {SHA1_CSV}")
    print("\nAll tasks complete.")


if __name__ == "__main__":
    main()