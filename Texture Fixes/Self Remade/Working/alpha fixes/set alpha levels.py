from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image


SOURCE_DIR = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Self Remade\Working\alpha fixes"
)

MAX_WORKERS = os.cpu_count() or 8


def pause_and_exit(code: int = 1) -> None:
    try:
        input("\nPress ENTER to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def find_pngs(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.png") if p.is_file()]


def process_image(path: Path) -> tuple[bool, str]:
    try:
        with Image.open(path) as img:
            img.load()

            if "A" not in img.getbands():
                return False, "no_alpha"

            alpha = img.getchannel("A")
            extrema = alpha.getextrema()

            # Fast skip: already only 0 and 128
            if extrema == (0, 0) or extrema == (128, 128):
                return False, "already_uniform"

            data = list(alpha.getdata())

            # Check if anything needs changing
            needs_change = any(v != 0 and v != 128 for v in data)
            if not needs_change:
                return False, "already_correct"

            # Apply transform
            new_data = [0 if v == 0 else 128 for v in data]

            alpha.putdata(new_data)

            img = img.copy()
            img.putalpha(alpha)

            temp_path = path.with_suffix(".tmp")

            img.save(temp_path, format="PNG", optimize=False)
            temp_path.replace(path)

            return True, "modified"

    except Exception as e:
        return False, f"error: {e}"


def main() -> None:
    if not SOURCE_DIR.exists():
        print(f"[ERROR] SOURCE_DIR does not exist:\n{SOURCE_DIR}")
        pause_and_exit(1)

    pngs = find_pngs(SOURCE_DIR)
    total = len(pngs)

    if total == 0:
        print("[INFO] No PNGs found.")
        pause_and_exit(0)

    print(f"[INFO] Found {total} PNGs")
    print("[INFO] Processing...\n")

    modified = 0
    checked = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_image, p): p for p in pngs}

        for future in as_completed(futures):
            changed, _ = future.result()
            checked += 1

            if changed:
                modified += 1

            if checked % 500 == 0 or checked == total:
                percent = (checked / total) * 100
                print(
                    f"\rProcessed {checked}/{total} ({percent:.2f}%) | Modified: {modified}",
                    end=""
                )

    print("\n\n[DONE]")
    print(f"Modified files: {modified}/{total}")

    pause_and_exit(0)


if __name__ == "__main__":
    main()