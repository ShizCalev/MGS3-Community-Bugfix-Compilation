from __future__ import annotations

import csv
import hashlib
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Tuple


# ============================================================
# CONFIG
# ============================================================

# Labels become CSV column suffixes: sha1_staging, sha1_staging_2x, sha1_staging_4x
FOLDER_LABELS = ("staging", "staging_2x", "staging_4x")

GROUPS = [
    {
        "name": r"hqtex - \ovr_stm\ovr_eu\_win",
        "folders": [
            ("staging",    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging\hqtex\flatlist\ovr_stm\ovr_eu\_win"),
            ("staging_2x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 2x Upscaled\hqtex\flatlist\ovr_stm\ovr_eu\_win"),
            ("staging_4x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 4x Upscaled\hqtex\flatlist\ovr_stm\ovr_eu\_win"),
        ],
    },
    {
        "name": r"hqtex - \ovr_stm\ovr_us\_win",
        "folders": [
            ("staging",    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging\hqtex\flatlist\ovr_stm\ovr_us\_win"),
            ("staging_2x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 2x Upscaled\hqtex\flatlist\ovr_stm\ovr_us\_win"),
            ("staging_4x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 4x Upscaled\hqtex\flatlist\ovr_stm\ovr_us\_win"),
        ],
    },
    {
        "name": r"hqtex - \ovr_stm\ovr_jp\_win",
        "folders": [
            ("staging",    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging\hqtex\flatlist\ovr_stm\ovr_jp\_win"),
            ("staging_2x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 2x Upscaled\hqtex\flatlist\ovr_stm\ovr_jp\_win"),
            ("staging_4x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 4x Upscaled\hqtex\flatlist\ovr_stm\ovr_jp\_win"),
        ],
    },
    {
        "name": r"standard - ovr_stm\ovr_eu\_win",
        "folders": [
            ("staging",    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging\textures\flatlist\ovr_stm\ovr_eu\_win"),
            ("staging_2x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 2x Upscaled\textures\flatlist\ovr_stm\ovr_eu\_win"),
            ("staging_4x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 4x Upscaled\textures\flatlist\ovr_stm\ovr_eu\_win"),
        ],
    },
    {
        "name": r"standard - ovr_stm\ovr_us\_win",
        "folders": [
            ("staging",    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging\textures\flatlist\ovr_stm\ovr_us\_win"),
            ("staging_2x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 2x Upscaled\textures\flatlist\ovr_stm\ovr_us\_win"),
            ("staging_4x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 4x Upscaled\textures\flatlist\ovr_stm\ovr_us\_win"),
        ],
    },
    {
        "name": r"standard - ovr_stm\ovr_jp\_win",
        "folders": [
            ("staging",    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging\textures\flatlist\ovr_stm\ovr_jp\_win"),
            ("staging_2x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 2x Upscaled\textures\flatlist\ovr_stm\ovr_jp\_win"),
            ("staging_4x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 4x Upscaled\textures\flatlist\ovr_stm\ovr_jp\_win"),
        ],
    },
    {
        "name": r"upscaled - base",
        "folders": [
            ("staging_2x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 2x Upscaled\textures\flatlist\ovr_stm\_win"),
            ("staging_4x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 4x Upscaled\textures\flatlist\ovr_stm\_win"),
        ],
    },
    {
        "name": r"upscaled - hqtex",
        "folders": [
            ("staging_2x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 2x Upscaled\hqtex\flatlist\ovr_stm\_win"),
            ("staging_4x", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging - 4x Upscaled\hqtex\flatlist\ovr_stm\_win"),
        ],
    },
    {
        "name": r"standard - hqtex",
        "folders": [
            ("staging", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging\hqtex\flatlist\_win"),
        ],
    },
    {
        "name": r"standard - base",
        "folders": [
            ("staging", r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Staging\textures\flatlist\_win"),
        ],
    },
]

OUTPUT_CSV = "smallest_common_stem_per_group.csv"
TEXTURE_FIXES_ROOT = r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes"

# Variant folder names immediately under TEXTURE_FIXES_ROOT
STAGING_VARIANTS = {"Staging", "Staging - 2x Upscaled", "Staging - 4x Upscaled"}


# ============================================================
# DATA TYPES
# ============================================================

@dataclass(frozen=True)
class FileSizeEntry:
    """Lightweight: just stem + size + path. No hash yet."""
    file_stem: str
    relative_path: str      # path relative to folder root (e.g. hqtex\flatlist\...\foo.bmp.ctxr)
    full_path: str
    size: int


@dataclass(frozen=True)
class GroupResult:
    group_name: str
    winning_stem: str
    relative_path: str      # relative path from folder root to winning file
    min_size: int
    total_size: int
    sha1_by_label: Dict[str, str]   # label -> sha1


# ============================================================
# HELPERS
# ============================================================

def extract_stem(file_path: Path) -> str:
    """
    Strip only the .ctxr extension, keep everything else.

    foo.bmp.ctxr       -> foo.bmp
    foo.bmp.bmp.ctxr   -> foo.bmp.bmp
    foo.ctxr           -> foo
    """
    name = file_path.name
    if name.lower().endswith(".ctxr"):
        return name[: -len(".ctxr")]
    return file_path.stem


def compute_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def get_staging_relative_path(file_path: Path) -> str:
    """
    Given a full path like:
        C:\\...\\Texture Fixes\\Staging - 4x Upscaled\\hqtex\\flatlist\\...\\foo.bmp.ctxr
    Return:
        hqtex\\flatlist\\...\\foo.bmp.ctxr

    Finds the Staging* variant component and returns everything after it.
    """
    parts = file_path.parts
    for i, part in enumerate(parts):
        if part in STAGING_VARIANTS:
            return str(Path(*parts[i + 1 :]))
    # Fallback: relative to TEXTURE_FIXES_ROOT, skip first component (variant folder)
    try:
        rel = file_path.relative_to(TEXTURE_FIXES_ROOT)
        rel_parts = rel.parts
        if len(rel_parts) > 1:
            return str(Path(*rel_parts[1:]))
    except ValueError:
        pass
    return file_path.name


def scan_folder_sizes(folder_root: Path) -> List[FileSizeEntry]:
    """Collect .ctxr stems + sizes. No hashing."""
    if not folder_root.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder_root}")

    results: List[FileSizeEntry] = []
    for path in folder_root.rglob("*.ctxr"):
        if path.is_file():
            try:
                results.append(FileSizeEntry(
                    file_stem=extract_stem(path).lower(),
                    relative_path=get_staging_relative_path(path),
                    full_path=str(path),
                    size=path.stat().st_size,
                ))
            except Exception as exc:
                print(f"[STAT FAIL] {path}: {exc}")

    print(f"[SCAN] {folder_root} -> {len(results)} .ctxr file(s)")
    return results


def group_by_stem(entries: List[FileSizeEntry]) -> DefaultDict[str, List[FileSizeEntry]]:
    grouped: DefaultDict[str, List[FileSizeEntry]] = defaultdict(list)
    for e in entries:
        grouped[e.file_stem].append(e)
    return grouped


def find_winner_stem(
    per_folder: List[Tuple[str, DefaultDict[str, List[FileSizeEntry]]]],
) -> Optional[Tuple[str, str, int, int]]:
    """
    Return (stem, relative_path, min_size, total_size) for smallest common stem,
    or None if no common stems.
    """
    if not per_folder:
        return None

    common_stems = set(per_folder[0][1].keys())
    for _, grouped in per_folder[1:]:
        common_stems &= set(grouped.keys())

    if not common_stems:
        return None

    best: Optional[Tuple[int, int, str]] = None

    for stem in common_stems:
        sizes: List[int] = []
        for _, grouped in per_folder:
            for entry in grouped[stem]:
                sizes.append(entry.size)

        key = (min(sizes), sum(sizes), stem)

        if best is None or key < best:
            best = key

    if best is None:
        return None

    winning_stem = best[2]

    # Grab relative_path from first folder that has the stem
    rel_path = ""
    for _, grouped in per_folder:
        entries = grouped.get(winning_stem, [])
        if entries:
            rel_path = entries[0].relative_path
            break

    return (winning_stem, rel_path, best[0], best[1])


def hash_winner_files(
    winning_stem: str,
    per_folder: List[Tuple[str, DefaultDict[str, List[FileSizeEntry]]]],
) -> Dict[str, str]:
    """Hash only the winning stem's files. Return label -> sha1."""
    sha1_by_label: Dict[str, str] = {}
    for label, grouped in per_folder:
        entries = grouped.get(winning_stem, [])
        if entries:
            try:
                sha1_by_label[label] = compute_sha1(Path(entries[0].full_path))
                print(f"  [HASH] [{label}] {entries[0].full_path}")
            except Exception as exc:
                print(f"  [HASH FAIL] [{label}] {entries[0].full_path}: {exc}")
                sha1_by_label[label] = ""
        else:
            sha1_by_label[label] = ""
    return sha1_by_label


def write_csv(out_path: Path, results: List[GroupResult]) -> None:
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    with tmp_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["group_name", "file_name", "relative_path"]
            + [f"sha1_{label}" for label in FOLDER_LABELS]
        )

        for result in results:
            writer.writerow(
                [result.group_name, result.winning_stem, result.relative_path]
                + [result.sha1_by_label.get(label, "") for label in FOLDER_LABELS]
            )

    os.replace(tmp_path, out_path)


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    if not GROUPS:
        print("[ERROR] No groups configured.")
        input("Press ENTER to exit...")
        return 1

    results: List[GroupResult] = []

    try:
        for group in GROUPS:
            group_name = str(group["name"])
            folder_entries: List[Tuple[str, Path]] = [
                (label, Path(path)) for label, path in group["folders"]
            ]

            if len(folder_entries) < 2:
                # Single folder: just find smallest .ctxr by size
                label, folder = folder_entries[0]
                print("=" * 100)
                print(f"[GROUP] {group_name} (single folder)")
                print(f"  [{label}] {folder}")
                print()

                entries = scan_folder_sizes(folder)
                if not entries:
                    print(f"[GROUP DONE] {group_name} -> no .ctxr files")
                    print()
                    continue

                smallest = min(entries, key=lambda e: (e.size, e.file_stem))

                print(f"  Hashing smallest: {smallest.file_stem}")
                try:
                    sha1 = compute_sha1(Path(smallest.full_path))
                    print(f"  [HASH] [{label}] {smallest.full_path}")
                except Exception as exc:
                    print(f"  [HASH FAIL] [{label}] {smallest.full_path}: {exc}")
                    sha1 = ""

                result = GroupResult(
                    group_name=group_name,
                    winning_stem=smallest.file_stem,
                    relative_path=smallest.relative_path,
                    min_size=smallest.size,
                    total_size=smallest.size,
                    sha1_by_label={label: sha1},
                )
                results.append(result)

                print(f"[GROUP DONE] {group_name}")
                print(f"  winning_stem : {result.winning_stem}")
                print(f"  size         : {result.min_size}")
                print(f"  sha1_{label:12s}: {sha1}")
                print()
                continue

            print("=" * 100)
            print(f"[GROUP] {group_name}")
            for label, folder in folder_entries:
                print(f"  [{label}] {folder}")
            print()

            # Phase 1: collect stems + sizes (no hashing)
            per_folder: List[Tuple[str, DefaultDict[str, List[FileSizeEntry]]]] = []
            for label, folder in folder_entries:
                entries = scan_folder_sizes(folder)
                per_folder.append((label, group_by_stem(entries)))

            # Phase 2: find smallest common stem
            winner_info = find_winner_stem(per_folder)

            if winner_info is None:
                print(f"[GROUP DONE] {group_name} -> no common stems")
                print()
                continue

            winning_stem, relative_path, min_size, total_size = winner_info

            # Phase 3: hash only the winner's files
            print(f"  Hashing winner: {winning_stem}")
            sha1_by_label = hash_winner_files(winning_stem, per_folder)

            result = GroupResult(
                group_name=group_name,
                winning_stem=winning_stem,
                relative_path=relative_path,
                min_size=min_size,
                total_size=total_size,
                sha1_by_label=sha1_by_label,
            )
            results.append(result)

            print(f"[GROUP DONE] {group_name}")
            print(f"  winning_stem : {result.winning_stem}")
            print(f"  min_size     : {result.min_size}")
            print(f"  total_size   : {result.total_size}")
            for label in FOLDER_LABELS:
                sha = result.sha1_by_label.get(label, "N/A")
                print(f"  sha1_{label:12s}: {sha}")
            print()

        out_path = Path(__file__).resolve().parent / OUTPUT_CSV
        write_csv(out_path, results)

        print(f"[DONE] Wrote CSV: {out_path}")
        print(f"[DONE] Groups with winners: {len(results)}")

    except Exception as exc:
        print(f"[FATAL] {exc}")
        input("Press ENTER to exit...")
        return 1

    input("Press ENTER to exit...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())