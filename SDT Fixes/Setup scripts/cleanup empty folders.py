from __future__ import annotations

import os
from pathlib import Path


def remove_empty_dirs(root: Path) -> int:
    removed = 0

    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        path = Path(dirpath)

        try:
            if not any(path.iterdir()):
                path.rmdir()
                removed += 1
                print(f"[REMOVED] {path}")
        except Exception as e:
            print(f"[ERR] {path}: {e}")

    return removed


def main() -> None:
    root = Path(__file__).resolve().parent

    print(f"Scanning for empty folders under:\n{root}\n")

    removed = remove_empty_dirs(root)

    print(f"\nDone. Removed {removed} empty folders.")


if __name__ == "__main__":
    main()