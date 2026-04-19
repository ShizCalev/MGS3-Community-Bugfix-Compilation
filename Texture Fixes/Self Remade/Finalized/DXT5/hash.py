from __future__ import annotations

import csv
import hashlib
import sys
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CSV_NAME = "dxt5_hashes.csv"


def wait_and_exit(code: int = 1) -> None:
    try:
        input("Press ENTER to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def sha1_file(path: Path) -> str:
    hasher = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def find_files_by_suffix(root: Path, suffix: str) -> list[Path]:
    return sorted(p for p in root.rglob(f"*{suffix}") if p.is_file())


def main() -> None:
    print(f"[INFO] Root: {SCRIPT_DIR}")

    ctxr_files = find_files_by_suffix(SCRIPT_DIR, ".ctxr")
    dds_files = find_files_by_suffix(SCRIPT_DIR, ".dds")

    print(f"[INFO] Found {len(ctxr_files)} .ctxr file(s)")
    print(f"[INFO] Found {len(dds_files)} .dds file(s)")

    # Preflight:
    # If any DDS exists without a matching CTXR beside it, list unique folders and exit.
    missing_ctxr_folders: set[Path] = set()

    for dds_path in dds_files:
        expected_ctxr = dds_path.with_suffix(".ctxr")
        if not expected_ctxr.is_file():
            missing_ctxr_folders.add(dds_path.parent)

    if missing_ctxr_folders:
        print()
        print("[ERROR] Found .dds file(s) missing a matching .ctxr beside them.")
        print("[ERROR] Unique folder(s):")
        for folder in sorted(missing_ctxr_folders):
            print(f"    {folder}")
        print()
        wait_and_exit(1)

    # Hash stage:
    # Build per-folder CSV rows for each .ctxr.
    rows_by_folder: dict[Path, list[dict[str, str]]] = defaultdict(list)
    dds_to_delete: list[Path] = []
    missing_required_files: list[str] = []

    for ctxr_path in ctxr_files:
        stem = ctxr_path.stem
        png_path = ctxr_path.with_suffix(".png")
        dds_path = ctxr_path.with_suffix(".dds")

        if not png_path.is_file():
            #missing_required_files.append(f"Missing PNG beside CTXR: {ctxr_path}")
            continue

        if not dds_path.is_file():
            missing_required_files.append(f"Missing DDS beside CTXR: {ctxr_path}")
            continue

        try:
            png_sha1 = sha1_file(png_path)
            dds_sha1 = sha1_file(dds_path)
            ctxr_sha1 = sha1_file(ctxr_path)
        except Exception as e:
            missing_required_files.append(f"Hashing failed for {ctxr_path}: {e}")
            continue

        rows_by_folder[ctxr_path.parent].append(
            {
                "filename": stem,
                "png_sha1": png_sha1,
                "dds_sha1": dds_sha1,
                "ctxr_sha1": ctxr_sha1,
            }
        )
        dds_to_delete.append(dds_path)

    if missing_required_files:
        print()
        print("[ERROR] One or more required sibling files were missing, or hashing failed.")
        for line in missing_required_files:
            print(f"    {line}")
        print()
        wait_and_exit(1)

    # Write CSVs only after all hashing succeeded.
    for folder, rows in sorted(rows_by_folder.items()):
        csv_path = folder / CSV_NAME
        rows.sort(key=lambda x: x["filename"].lower())

        try:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["filename", "png_sha1", "dds_sha1", "ctxr_sha1"],
                )
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            print()
            print(f"[ERROR] Failed to write CSV: {csv_path}")
            print(f"        {e}")
            print()
            wait_and_exit(1)

    # Delete DDS files only after every hash + CSV write succeeded.
    delete_failures: list[str] = []

    for dds_path in dds_to_delete:
        try:
            dds_path.unlink()
        except Exception as e:
            delete_failures.append(f"{dds_path} -> {e}")

    print()
    print(f"[DONE] Wrote {sum(len(v) for v in rows_by_folder.values())} CSV row(s) across {len(rows_by_folder)} folder(s).")
    print(f"[DONE] Deleted {len(dds_to_delete) - len(delete_failures)} .dds file(s).")

    if delete_failures:
        print()
        print("[WARNING] Some .dds files could not be deleted:")
        for line in delete_failures:
            print(f"    {line}")
        print()
        wait_and_exit(1)

    wait_and_exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("[ERROR] Interrupted by user.")
        wait_and_exit(1)
    except SystemExit:
        raise
    except Exception as e:
        print()
        print(f"[FATAL] {e}")
        wait_and_exit(1)