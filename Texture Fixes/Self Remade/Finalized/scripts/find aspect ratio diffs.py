from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


SOURCE_DIR = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Self Remade\Finalized\Dont demaster\UI\ctrltype_ps2\_win"
)
COMPARE_ROOT = Path(
    r"D:\MG Textures\MGS3\Base Textures\textures\flatlist\ovr_stm\ctrltype_ps4\_win"
)
LOG_FILE = SOURCE_DIR / "resolution_comparison_log.txt"


def pause_and_exit(code: int = 1) -> None:
    try:
        input("\nPress ENTER to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def get_png_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def build_compare_map(compare_root: Path) -> tuple[dict[str, Path], list[str]]:
    compare_map: dict[str, Path] = {}
    duplicate_names: dict[str, list[Path]] = {}

    for path in sorted(compare_root.rglob("*.png")):
        name_lower = path.name.lower()

        if name_lower in compare_map:
            duplicate_names.setdefault(name_lower, [compare_map[name_lower]]).append(path)
            continue

        compare_map[name_lower] = path

    duplicate_log_lines: list[str] = []

    if duplicate_names:
        duplicate_log_lines.append("DUPLICATE FILENAMES FOUND IN COMPARE ROOT")
        duplicate_log_lines.append("Only the first discovered file was used for comparison.")
        duplicate_log_lines.append("")

        for name_lower in sorted(duplicate_names):
            duplicate_log_lines.append(name_lower)
            for dup_path in duplicate_names[name_lower]:
                duplicate_log_lines.append(f"  {dup_path}")
            duplicate_log_lines.append("")

    return compare_map, duplicate_log_lines


def main() -> None:
    if not SOURCE_DIR.is_dir():
        print(f"ERROR: SOURCE_DIR does not exist:\n{SOURCE_DIR}")
        pause_and_exit(1)

    if not COMPARE_ROOT.is_dir():
        print(f"ERROR: COMPARE_ROOT does not exist:\n{COMPARE_ROOT}")
        pause_and_exit(1)

    source_pngs = sorted(SOURCE_DIR.glob("*.png"))

    if not source_pngs:
        print(f"ERROR: No PNG files found in:\n{SOURCE_DIR}")
        pause_and_exit(1)

    compare_map, duplicate_log_lines = build_compare_map(COMPARE_ROOT)

    lines: list[str] = []
    lines.append(f"Source folder: {SOURCE_DIR}")
    lines.append(f"Compare root: {COMPARE_ROOT}")
    lines.append("")
    lines.append(f"Total source PNGs: {len(source_pngs)}")
    lines.append("")

    matches = 0
    mismatches = 0
    missing = 0
    errors = 0

    for source_path in source_pngs:
        compare_path = compare_map.get(source_path.name.lower())

        if compare_path is None:
            missing += 1
            lines.append(f"[MISSING] {source_path.name}")
            lines.append(f"  Source:  {source_path}")
            lines.append("  Compare: NOT FOUND")
            lines.append("")
            continue

        try:
            source_size = get_png_size(source_path)
        except Exception as exc:
            errors += 1
            lines.append(f"[ERROR] {source_path.name}")
            lines.append(f"  Failed reading source image: {source_path}")
            lines.append(f"  Error: {exc}")
            lines.append("")
            continue

        try:
            compare_size = get_png_size(compare_path)
        except Exception as exc:
            errors += 1
            lines.append(f"[ERROR] {source_path.name}")
            lines.append(f"  Failed reading compare image: {compare_path}")
            lines.append(f"  Error: {exc}")
            lines.append("")
            continue

        if source_size == compare_size:
            matches += 1
            continue  # do not log matches

        mismatches += 1
        lines.append(f"[MISMATCH] {source_path.name}")
        lines.append(f"  Source:  {source_path} -> {source_size[0]}x{source_size[1]}")
        lines.append(f"  Compare: {compare_path} -> {compare_size[0]}x{compare_size[1]}")
        lines.append("")

    lines.append("SUMMARY")
    lines.append(f"  Matches:    {matches}")
    lines.append(f"  Mismatches: {mismatches}")
    lines.append(f"  Missing:    {missing}")
    lines.append(f"  Errors:     {errors}")
    lines.append("")

    if duplicate_log_lines:
        lines.append("")
        lines.extend(duplicate_log_lines)

    try:
        LOG_FILE.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    except Exception as exc:
        print(f"ERROR: Failed to write log file:\n{LOG_FILE}\n\n{exc}")
        pause_and_exit(1)

    print(f"Done. Log written to:\n{LOG_FILE}")


if __name__ == "__main__":
    main()