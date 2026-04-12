from __future__ import annotations

import hashlib
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


PS2_SOURCE_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\ps2 textures"
)
MC_SOURCE_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\mc textures"
)

PS2_TARGET_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\hires textures\ps2 textures"
)
MC_TARGET_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\hires textures\mc textures"
)

FILENAME_LIST_PATH = Path(
    r"C:\Development\Git\MGS3-PS2-Textures\Tri-Dumped\Master Collection\Metadata\mgs3_hires_same_as_standard_textures.txt"
)

MAX_WORKERS = max(4, os.cpu_count() or 4)
HASH_CHUNK_SIZE = 8 * 1024 * 1024


def pause_and_exit(code: int = 0) -> None:
    try:
        input("\nPress ENTER to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def sha1_of_file(path: Path) -> str:
    sha1 = hashlib.sha1()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            sha1.update(chunk)

    return sha1.hexdigest()


def files_match(source: Path, destination: Path) -> bool:
    if not destination.is_file():
        return False

    try:
        source_stat = source.stat()
        destination_stat = destination.stat()
    except OSError:
        return False

    if source_stat.st_size != destination_stat.st_size:
        return False

    return sha1_of_file(source) == sha1_of_file(destination)


def load_allowed_names(txt_path: Path) -> set[str]:
    if not txt_path.is_file():
        raise FileNotFoundError(f"Filename list not found: {txt_path}")

    allowed: set[str] = set()

    with txt_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            allowed.add(line)

    return allowed


def gather_matching_pngs(
    source_root: Path,
    allowed_names: set[str],
) -> dict[Path, Path]:
    if not source_root.is_dir():
        raise NotADirectoryError(f"Source folder not found: {source_root}")

    matches: dict[Path, Path] = {}

    for source_path in source_root.rglob("*.png"):
        if not source_path.is_file():
            continue

        exact_name_without_png = source_path.stem

        if exact_name_without_png not in allowed_names:
            continue

        relative_path = source_path.relative_to(source_root)

        if relative_path in matches:
            raise RuntimeError(
                "Duplicate relative path encountered during source scan:\n"
                f"  Root: {source_root}\n"
                f"  Relative path: {relative_path}"
            )

        matches[relative_path] = source_path

    return matches


def ensure_parent_folder(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_one(source_path: Path, destination_path: Path) -> str:
    ensure_parent_folder(destination_path)

    if files_match(source_path, destination_path):
        return "unchanged"

    shutil.copy2(source_path, destination_path)
    return "copied"


def delete_one(path: Path) -> str:
    try:
        path.unlink()
        return "deleted"
    except FileNotFoundError:
        return "missing"


def remove_empty_dirs(root: Path) -> int:
    removed = 0

    if not root.is_dir():
        return removed

    for current_root, dirnames, filenames in os.walk(root, topdown=False):
        current_path = Path(current_root)

        if current_path == root:
            continue

        if dirnames or filenames:
            continue

        try:
            current_path.rmdir()
            removed += 1
        except OSError:
            pass

    return removed


def sync_tree(
    source_root: Path,
    target_root: Path,
    allowed_names: set[str],
    label: str,
) -> None:
    print(f"\n=== {label} ===")
    print(f"Source: {source_root}")
    print(f"Target: {target_root}")

    desired_map = gather_matching_pngs(source_root, allowed_names)
    desired_relative_paths = set(desired_map.keys())

    print(f"Matched source PNGs: {len(desired_relative_paths)}")

    existing_target_files = [
        path
        for path in target_root.rglob("*")
        if path.is_file()
    ] if target_root.is_dir() else []

    delete_candidates: list[Path] = []

    for target_file in existing_target_files:
        relative_path = target_file.relative_to(target_root)

        if relative_path not in desired_relative_paths:
            delete_candidates.append(target_file)

    print(f"Files to delete from target: {len(delete_candidates)}")

    deleted_count = 0
    missing_delete_count = 0

    if delete_candidates:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(delete_one, path): path
                for path in delete_candidates
            }

            for future in as_completed(futures):
                result = future.result()

                if result == "deleted":
                    deleted_count += 1
                elif result == "missing":
                    missing_delete_count += 1

    print(f"Deleted: {deleted_count}")
    if missing_delete_count:
        print(f"Already missing during delete pass: {missing_delete_count}")

    copy_jobs = [
        (source_path, target_root / relative_path)
        for relative_path, source_path in desired_map.items()
    ]

    copied_count = 0
    unchanged_count = 0

    if copy_jobs:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(copy_one, source_path, destination_path): (source_path, destination_path)
                for source_path, destination_path in copy_jobs
            }

            for future in as_completed(futures):
                result = future.result()

                if result == "copied":
                    copied_count += 1
                elif result == "unchanged":
                    unchanged_count += 1

    removed_dirs = remove_empty_dirs(target_root)

    print(f"Copied/updated: {copied_count}")
    print(f"Already up to date: {unchanged_count}")
    print(f"Empty folders removed: {removed_dirs}")


def main() -> None:
    try:
        allowed_names = load_allowed_names(FILENAME_LIST_PATH)

        print(f"Loaded exact filename list entries: {len(allowed_names)}")
        print(f"Using {MAX_WORKERS} worker threads")

        sync_tree(
            source_root=PS2_SOURCE_ROOT,
            target_root=PS2_TARGET_ROOT,
            allowed_names=allowed_names,
            label="PS2 -> hires ps2",
        )

        sync_tree(
            source_root=MC_SOURCE_ROOT,
            target_root=MC_TARGET_ROOT,
            allowed_names=allowed_names,
            label="MC -> hires mc",
        )

        print("\nDone.")
        pause_and_exit(0)

    except Exception as exc:
        print(f"\nERROR: {exc}")
        pause_and_exit(1)


if __name__ == "__main__":
    main()