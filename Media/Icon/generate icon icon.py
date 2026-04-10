from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


ICON_SIZES: list[tuple[int, int]] = [
    (16, 16),
    (24, 24),
    (32, 32),
    (40, 40),
    (48, 48),
    (64, 64),
    (72, 72),
    (96, 96),
    (128, 128),
    (256, 256),
]


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


def main() -> None:
    script_dir = get_script_dir()
    input_png = script_dir / "icon.png"
    output_ico = script_dir / "icon.ico"

    if not input_png.is_file():
        print(f"ERROR: Missing input file: {input_png}")
        pause_and_exit(1)

    try:
        with Image.open(input_png) as img:
            img = img.convert("RGBA")

            max_required_width = max(size[0] for size in ICON_SIZES)
            max_required_height = max(size[1] for size in ICON_SIZES)

            if img.width < max_required_width or img.height < max_required_height:
                print(
                    "ERROR: icon.png is too small.\n"
                    f"Current size: {img.width}x{img.height}\n"
                    f"Required minimum: {max_required_width}x{max_required_height}"
                )
                pause_and_exit(1)

            img.save(output_ico, format="ICO", sizes=ICON_SIZES)

    except Exception as exc:
        print(f"ERROR: Failed to create ICO.\n{exc}")
        pause_and_exit(1)

    print(f"Created: {output_ico}")


if __name__ == "__main__":
    main()