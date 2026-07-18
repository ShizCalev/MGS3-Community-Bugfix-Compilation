from pathlib import Path
from PIL import Image
import sys


def force_alpha_128(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")

    with Image.open(path) as im:
        rgba = im.convert("RGBA")
        r, g, b, a = rgba.split()

        # Replace alpha with constant 128
        new_alpha = Image.new("L", rgba.size, 128)

        out = Image.merge("RGBA", (r, g, b, new_alpha))
        out.save(path, format="PNG", optimize=False)


def main():
    script_dir = Path(__file__).resolve().parent
    target = script_dir / "s001a_enkei1_rep.bmp.png"

    try:
        force_alpha_128(target)
        print(f"[OK] Forced 128 alpha: {target}")
    except Exception as e:
        print(f"[ERROR] {e}")
        input("Press ENTER to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()