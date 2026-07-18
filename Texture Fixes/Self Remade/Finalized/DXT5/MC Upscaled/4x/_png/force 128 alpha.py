import sys
from pathlib import Path
from PIL import Image

TARGET_FILES = [
    "s001a_soil01_rep_mip8000.bmp.png",
    "s001a_enkei1_rep.bmp.png",
    "v000a_kinokatamari_a02_rep.bmp.png",
]


def is_alpha_128(img):
    if img.mode != "RGBA":
        return False
    alpha = img.getchannel("A")
    return all(v == 128 for v in alpha.getdata())


def force_alpha_128(img):
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    r, g, b, _ = img.split()
    alpha = Image.new("L", img.size, 128)
    return Image.merge("RGBA", (r, g, b, alpha))


def process_file(path):
    if not path.exists():
        print(f"[MISSING] {path}")
        return

    try:
        img = Image.open(path)

        if is_alpha_128(img):
            print(f"[SKIP] Already correct: {path.name}")
            return

        fixed = force_alpha_128(img)
        fixed.save(path, optimize=False)

        print(f"[FIXED] {path.name}")

    except Exception as e:
        print(f"[ERROR] {path}: {e}")


def main():
    base_dir = Path(__file__).resolve().parent

    for name in TARGET_FILES:
        process_file(base_dir / name)

    print("\nDone. Press ENTER to exit...")
    input()


if __name__ == "__main__":
    main()