import os
from pathlib import Path
from PIL import Image

IMAGE_EXTS = {".png"}

def next_power_of_two(n: int) -> int:
    if n <= 0:
        return 1
    return 1 << (n - 1).bit_length()

def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0

def process_file(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            width, height = img.size

            if is_power_of_two(width) and is_power_of_two(height):
                return False

            new_width = next_power_of_two(width)
            new_height = next_power_of_two(height)

            print(f"[PAD] {path} : {width}x{height} -> {new_width}x{new_height}")

            # Ensure RGBA so we can pad with transparent pixels
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Create empty canvas (fully transparent)
            padded = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))

            # Paste original image bottom-right
            offset_x = new_width - width
            offset_y = new_height - height
            padded.paste(img, (offset_x, offset_y))

            padded.save(path, optimize=False)
            return True

    except Exception as e:
        print(f"[ERROR] {path} : {e}")
        return False

def main() -> None:
    root = Path(__file__).resolve().parent

    files = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() in IMAGE_EXTS:
                files.append(path)

    padded_count = 0

    for path in files:
        if process_file(path):
            padded_count += 1

    print()
    print(f"[DONE] Checked: {len(files)}")
    print(f"[DONE] Padded: {padded_count}")
    input("Press ENTER to exit...")

if __name__ == "__main__":
    main()