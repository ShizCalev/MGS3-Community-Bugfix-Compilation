from __future__ import annotations

import os
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


SCRIPT_DIR = Path(__file__).resolve().parent
MAX_WORKERS = max(os.cpu_count() or 4, 4)


def wait_and_exit(code: int = 0) -> None:
    try:
        input("Press ENTER to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def collect_pngs(root: Path) -> list[Path]:
    return [
        p for p in root.rglob("*.png")
        if p.is_file() and "_png" not in p.parts
    ]


def move_png(png_path: Path) -> tuple[bool, str]:
    try:
        target_dir = png_path.parent / "_png"
        target_dir.mkdir(exist_ok=True)

        target_path = target_dir / png_path.name

        # Handle collisions
        if target_path.exists():
            # If same file (rare), just delete source
            if png_path.resolve() == target_path.resolve():
                return True, f"Skipped (same path): {png_path}"

            stem = target_path.stem
            suffix = target_path.suffix
            counter = 1
            while True:
                new_target = target_dir / f"{stem}_{counter}{suffix}"
                if not new_target.exists():
                    target_path = new_target
                    break
                counter += 1

        shutil.move(str(png_path), str(target_path))
        return True, f"Moved: {png_path} -> {target_path}"

    except Exception as e:
        return False, f"{png_path} -> {e}"


def main() -> None:
    print(f"[INFO] Root: {SCRIPT_DIR}")

    pngs = collect_pngs(SCRIPT_DIR)
    print(f"[INFO] Found {len(pngs)} PNG file(s) to move")

    if not pngs:
        wait_and_exit(0)

    moved = 0
    failed: list[str] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(move_png, p) for p in pngs]

        for future in as_completed(futures):
            ok, msg = future.result()
            if ok:
                moved += 1
            else:
                failed.append(msg)

    print()
    print(f"[DONE] Moved {moved} PNG file(s)")

    if failed:
        print()
        print("[ERROR] Some files failed to move:")
        for line in failed:
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