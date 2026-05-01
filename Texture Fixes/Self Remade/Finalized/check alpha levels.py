from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import os


MAX_WORKERS = max(1, os.cpu_count() or 2)


def get_alpha_levels(png_path: Path):
    with Image.open(png_path) as im:
        rgba = im.convert("RGBA")
        alpha = rgba.getchannel("A")
        levels = sorted(set(alpha.getdata()))
    return png_path.name, levels


def main():
    base_dir = Path(__file__).resolve().parent
    png_files = sorted(base_dir.glob("*.png"))

    if not png_files:
        print("No PNG files found.")
        input("\nPress ENTER to exit...")
        return

    print(f"Processing {len(png_files)} PNG(s) with {MAX_WORKERS} worker(s)...\n")

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(get_alpha_levels, png) for png in png_files]

        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"[ERROR] {e}")

    # sort output by filename for consistency
    results.sort(key=lambda x: x[0])

    for name, levels in results:
        print(f"{name}: {levels}")

    input("\nPress ENTER to exit...")


if __name__ == "__main__":
    main()