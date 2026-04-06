from __future__ import annotations

import csv
import hashlib
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# ==========================================================
# CONFIGURATION
# ==========================================================
SCRIPT = Path(
    r"C:\Development\Git\Afevis-MGS2-Bugfix-Compilation\external\SDT-Tools\0000.SDT_extractor.py"
)
THREADS = os.cpu_count() or 8
DEST_ROOT = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\better_audio_scripts")
SHA1_CSV = DEST_ROOT / "_csv_sha1s.csv"
SHA1_BUFFER_SIZE = 8 * 1024 * 1024


# ==========================================================
# HELPERS
# ==========================================================
def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(SHA1_BUFFER_SIZE), b""):
            h.update(chunk)

    return h.hexdigest()


# ==========================================================
# MAIN LOGIC
# ==========================================================
def process_file(sdt_path: Path, repo_root: Path) -> str:
    rel_path = sdt_path.relative_to(repo_root)
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
    repo_root = Path.cwd()
    sdt_files = list(repo_root.rglob("*.sdt"))

    if not sdt_files:
        print("No .sdt files found recursively under current directory.")
        return

    print(f"Found {len(sdt_files)} .sdt files. Processing with {THREADS} threads...\n")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(process_file, f, repo_root): f for f in sdt_files}
        for fut in as_completed(futures):
            print(fut.result())

    sha1_rows: list[tuple[str, str]] = []

    for sdt_path in sdt_files:
        rel_path = sdt_path.relative_to(repo_root)
        csv_path = DEST_ROOT / rel_path.with_suffix(".csv")

        if not csv_path.is_file():
            continue

        csv_rel_path = csv_path.relative_to(DEST_ROOT).as_posix()
        original_sha1 = sha1_of_file(csv_path)
        sha1_rows.append((csv_rel_path, original_sha1))

    sha1_rows.sort(key=lambda row: row[0].lower())

    SHA1_CSV.parent.mkdir(parents=True, exist_ok=True)

    with SHA1_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["relative_csv_path", "original_sha1"])
        writer.writerows(sha1_rows)

    print(f"\nWrote SHA1 CSV: {SHA1_CSV}")
    print("\nAll tasks complete.")


# ==========================================================
# ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    main()