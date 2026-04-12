from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image


ROOT_DIR = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Self Remade\Finalized")
MAX_WORKERS = max(4, os.cpu_count() or 4)


def pause_and_exit(code: int = 0) -> None:
    try:
        input("Press ENTER to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def find_images(root: Path) -> list[Path]:
    return [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in (".png", ".tga")
    ]


def clamp_alpha_in_place(path: Path) -> bool:
    """
    Returns True if file was modified.
    """
    try:
        with Image.open(path) as im:
            if im.mode not in ("RGBA", "LA"):
                return False

            alpha = im.getchannel("A")

            # Fast skip if already valid
            _min, max_a = alpha.getextrema()
            if max_a <= 128:
                return False

            # Clamp alpha
            # LUT is fastest possible way here
            lut = [i if i <= 128 else 128 for i in range(256)]
            new_alpha = alpha.point(lut)

            # Merge back without touching RGB
            if im.mode == "RGBA":
                r, g, b, _ = im.split()
                new_im = Image.merge("RGBA", (r, g, b, new_alpha))
            else:  # LA
                l, _ = im.split()
                new_im = Image.merge("LA", (l, new_alpha))

            # Atomic write
            with tempfile.NamedTemporaryFile(delete=False, dir=path.parent, suffix=path.suffix) as tmp:
                tmp_path = Path(tmp.name)

            try:
                new_im.save(tmp_path, format=im.format, optimize=False)
                tmp_path.replace(path)
            finally:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass

            return True

    except Exception:
        return False


def main() -> None:
    if not ROOT_DIR.is_dir():
        print(f"ERROR: Missing folder: {ROOT_DIR}")
        pause_and_exit(1)

    files = find_images(ROOT_DIR)
    total = len(files)

    if total == 0:
        print("No PNG/TGA files found.")
        pause_and_exit(0)

    print(f"Processing {total} files with {MAX_WORKERS} threads...")

    modified = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(clamp_alpha_in_place, f): f for f in files}

        for i, future in enumerate(as_completed(futures), 1):
            try:
                if future.result():
                    modified += 1
            except Exception:
                pass

            if i % 100 == 0 or i == total:
                print(f"{i}/{total} processed... modified: {modified}")

    print(f"\nDone. Modified {modified} files.")
    pause_and_exit(0)


if __name__ == "__main__":
    main()