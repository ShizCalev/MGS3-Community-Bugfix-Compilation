from __future__ import annotations

import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Iterable

from PIL import Image


STEMS_FILE = Path(
    r"C:\Development\Git\MGS3-PS2-Textures\Tri-Dumped\Master Collection\Metadata\mgs3_mc_dxt5_stems_with_128_alpha.txt"
)

STANDARD_SOURCE_DIR = Path(
    r"D:\MG Textures\MGS3\Base Textures\textures\flatlist\_win"
)
HQTEX_SOURCE_DIR = Path(
    r"D:\MG Textures\MGS3_HiRes\flatlist\_win"
)

STANDARD_OUTPUT_DIR = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Self Remade\Finalized\DXT5\Base Fixes\standard"
)
HQTEX_OUTPUT_DIR = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Self Remade\Finalized\DXT5\Base Fixes\hqtex"
)

PNG_EXT = ".png"
MAX_WORKERS = max(4, os.cpu_count() or 4)

print_lock = Lock()


def log(message: str) -> None:
    with print_lock:
        print(message, flush=True)


def fatal(message: str) -> None:
    log(f"[FATAL] {message}")
    input("Press ENTER to exit...")
    sys.exit(1)


def read_stems(path: Path) -> list[str]:
    if not path.is_file():
        fatal(f"Missing stems file: {path}")

    stems: list[str] = []
    seen: set[str] = set()

    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            stem = raw_line.strip()
            if not stem:
                continue
            if stem.startswith(";") or stem.startswith("//"):
                continue
            key = stem.lower()
            if key in seen:
                continue
            seen.add(key)
            stems.append(stem)

    return stems


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def image_alpha_is_all_128(path: Path) -> bool:
    with Image.open(path) as im:
        if "A" not in im.getbands():
            return False

        alpha = im.getchannel("A")
        lo, hi = alpha.getextrema()
        return lo == 128 and hi == 128


def save_with_alpha_128_atomic(src_path: Path, dst_dir: Path, stem: str) -> Path:
    ensure_dir(dst_dir)

    final_path = dst_dir / f"{stem}{PNG_EXT}"
    tmp_path = dst_dir / f"{stem}_tmp{PNG_EXT}"

    with Image.open(src_path) as im:
        rgba = im.convert("RGBA")
        r, g, b, _a = rgba.split()
        alpha_128 = Image.new("L", rgba.size, 128)
        out = Image.merge("RGBA", (r, g, b, alpha_128))
        out.save(tmp_path, format="PNG", optimize=False)

    os.replace(tmp_path, final_path)
    return final_path


def process_one(
    stem: str,
    src_dir: Path,
    dst_dir: Path,
    label: str,
) -> tuple[str, str, str]:
    src_path = src_dir / f"{stem}{PNG_EXT}"

    if not src_path.is_file():
        return ("missing", label, stem)

    try:
        if image_alpha_is_all_128(src_path):
            return ("ok", label, stem)

        out_path = save_with_alpha_128_atomic(src_path, dst_dir, stem)
        return ("fixed", label, str(out_path))
    except Exception as exc:
        return ("error", label, f"{stem}: {exc}")


def build_jobs(stems: Iterable[str]) -> list[tuple[str, Path, Path, str]]:
    jobs: list[tuple[str, Path, Path, str]] = []

    for stem in stems:
        jobs.append((stem, STANDARD_SOURCE_DIR, STANDARD_OUTPUT_DIR, "standard"))
        jobs.append((stem, HQTEX_SOURCE_DIR, HQTEX_OUTPUT_DIR, "hqtex"))

    return jobs


def main() -> None:
    for required_dir in (
        STANDARD_SOURCE_DIR,
        HQTEX_SOURCE_DIR,
    ):
        if not required_dir.is_dir():
            fatal(f"Missing source directory: {required_dir}")

    ensure_dir(STANDARD_OUTPUT_DIR)
    ensure_dir(HQTEX_OUTPUT_DIR)

    stems = read_stems(STEMS_FILE)
    if not stems:
        fatal(f"No stems found in: {STEMS_FILE}")

    jobs = build_jobs(stems)

    log(f"[INFO] Loaded stems: {len(stems)}")
    log(f"[INFO] Total jobs: {len(jobs)}")
    log(f"[INFO] MAX_WORKERS: {MAX_WORKERS}")

    fixed_count = 0
    ok_count = 0
    missing_count = 0
    error_count = 0

    missing_standard: list[str] = []
    missing_hqtex: list[str] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(process_one, stem, src_dir, dst_dir, label)
            for stem, src_dir, dst_dir, label in jobs
        ]

        completed = 0
        total = len(futures)

        for future in as_completed(futures):
            completed += 1
            status, label, payload = future.result()

            if status == "fixed":
                fixed_count += 1
                log(f"[FIXED] [{label}] {payload}")
            elif status == "ok":
                ok_count += 1
            elif status == "missing":
                missing_count += 1
                if label == "standard":
                    missing_standard.append(payload)
                else:
                    missing_hqtex.append(payload)
                log(f"[MISSING] [{label}] {payload}")
            else:
                error_count += 1
                errors.append(f"[{label}] {payload}")
                log(f"[ERROR] [{label}] {payload}")

            if completed % 100 == 0 or completed == total:
                log(
                    f"[PROGRESS] {completed}/{total} | fixed={fixed_count} ok={ok_count} missing={missing_count} errors={error_count}"
                )

    print()
    log("============== SUMMARY ==============")
    log(f"Stems loaded: {len(stems)}")
    log(f"Jobs processed: {len(jobs)}")
    log(f"Already correct: {ok_count}")
    log(f"Fixed and copied: {fixed_count}")
    log(f"Missing: {missing_count}")
    log(f"Errors: {error_count}")

    if missing_standard:
        log("")
        log("[MISSING STANDARD]")
        for stem in sorted(missing_standard, key=str.lower):
            log(stem)

    if missing_hqtex:
        log("")
        log("[MISSING HQTEX]")
        for stem in sorted(missing_hqtex, key=str.lower):
            log(stem)

    if errors:
        log("")
        log("[ERRORS]")
        for error in errors:
            log(error)
        input("Press ENTER to exit...")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        fatal("Interrupted by user.")
    except Exception:
        log(traceback.format_exc())
        input("Press ENTER to exit...")
        sys.exit(1)