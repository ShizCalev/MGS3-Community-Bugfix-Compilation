from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image


def pause_and_exit(code: int = 1) -> None:
    try:
        input("\nPress ENTER to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def get_script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_pngs(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.png")
        if path.is_file()
    )


def find_dds_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.dds")
        if path.is_file()
    )


def normalize_for_png_save(img: Image.Image) -> Image.Image:
    if img.mode in ("P", "PA"):
        return img.convert("RGBA")
    if img.mode == "LA":
        return img.convert("RGBA")
    if img.mode not in ("1", "L", "LA", "RGB", "RGBA"):
        return img.convert("RGBA")
    return img


def resave_png(path: Path) -> tuple[bool, str]:
    temp_path = path.with_name(path.name + ".tmp")

    try:
        with Image.open(path) as img:
            img.load()
            save_image = normalize_for_png_save(img)
            save_image.save(
                temp_path,
                format="PNG",
                optimize=False,
            )

        os.replace(temp_path, path)
        return True, str(path)

    except Exception as exc:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

        return False, f"{path} -> {exc}"


def convert_dds_to_png_and_delete_dds(path: Path) -> tuple[bool, str]:
    png_path = path.with_suffix(".png")
    temp_path = png_path.with_name(png_path.name + ".tmp")

    try:
        with Image.open(path) as img:
            img.load()
            save_image = normalize_for_png_save(img)
            save_image.save(
                temp_path,
                format="PNG",
                optimize=False,
            )

        os.replace(temp_path, png_path)
        path.unlink()

        return True, str(path)

    except Exception as exc:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

        return False, f"{path} -> {exc}"


def main() -> None:
    root = get_script_dir()

    dds_files = find_dds_files(root)
    png_files = find_pngs(root)

    if not dds_files and not png_files:
        print(f"No DDS or PNG files found under: {root}")
        return

    max_workers = min(32, max(1, (os.cpu_count() or 1) * 2))

    total_tasks = len(dds_files) + len(png_files)

    print(f"Root: {root}")
    print(f"DDS files found: {len(dds_files)}")
    print(f"PNG files found: {len(png_files)}")
    print(f"Worker threads: {max_workers}")
    print("Converting DDS to PNG, deleting DDS on success, and resaving PNG files with PIL optimize=False...\n")

    start_time = time.time()
    completed = 0
    succeeded = 0
    failed = 0
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}

        for path in dds_files:
            futures[executor.submit(convert_dds_to_png_and_delete_dds, path)] = ("dds", path)

        for path in png_files:
            futures[executor.submit(resave_png, path)] = ("png", path)

        for future in as_completed(futures):
            completed += 1

            ok, message = future.result()
            if ok:
                succeeded += 1
            else:
                failed += 1
                failures.append(message)

            print(
                f"\rProcessed: {completed}/{total_tasks} | "
                f"Succeeded: {succeeded} | Failed: {failed}",
                end="",
                flush=True,
            )

    elapsed = time.time() - start_time

    print("\n")
    print(f"Done in {elapsed:.2f} seconds.")
    print(f"Succeeded: {succeeded}")
    print(f"Failed: {failed}")

    if failures:
        log_path = root / "dds_png_failures.txt"
        log_path.write_text("\n".join(failures) + "\n", encoding="utf-8", newline="\n")
        print(f"Failure log written to: {log_path}")

        for failure in failures[:20]:
            print(f"  {failure}")

        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        pause_and_exit(1)
    except Exception as exc:
        print(f"\nFatal error: {exc}")
        pause_and_exit(1)