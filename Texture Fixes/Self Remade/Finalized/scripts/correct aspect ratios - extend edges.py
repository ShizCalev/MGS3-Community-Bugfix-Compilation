from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image


def get_script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


SOURCE_DIR = get_script_dir()

COMPARE_ROOT = Path(
    r"D:\MG Textures\MGS3\Base Textures\textures\flatlist\_win"
)
LOG_FILE = SOURCE_DIR / "aspect_padding_log.txt"


def pause_and_exit(code: int = 1) -> None:
    try:
        input("\nPress ENTER to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def get_image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def load_rgba(path: Path) -> Image.Image:
    with Image.open(path) as img:
        return img.convert("RGBA")


def build_compare_map(compare_root: Path) -> tuple[dict[str, Path], list[str]]:
    compare_map: dict[str, Path] = {}
    duplicate_names: dict[str, list[Path]] = {}

    for path in sorted(compare_root.rglob("*.png")):
        name_lower = path.name.lower()

        if name_lower in compare_map:
            duplicate_names.setdefault(name_lower, [compare_map[name_lower]]).append(path)
            continue

        compare_map[name_lower] = path

    duplicate_log_lines: list[str] = []

    if duplicate_names:
        duplicate_log_lines.append("DUPLICATE FILENAMES FOUND IN COMPARE ROOT")
        duplicate_log_lines.append("Only the first discovered file was used for comparison.")
        duplicate_log_lines.append("")

        for name_lower in sorted(duplicate_names):
            duplicate_log_lines.append(name_lower)
            for dup_path in duplicate_names[name_lower]:
                duplicate_log_lines.append(f"  {dup_path}")
            duplicate_log_lines.append("")

    return compare_map, duplicate_log_lines


def same_aspect_ratio(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> bool:
    return source_width * target_height == target_width * source_height


def get_minimum_padded_size_for_target_aspect(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> tuple[int, int]:
    gcd_value = math.gcd(target_width, target_height)
    ratio_width = target_width // gcd_value
    ratio_height = target_height // gcd_value

    multiplier = max(
        math.ceil(source_width / ratio_width),
        math.ceil(source_height / ratio_height),
    )

    new_width = ratio_width * multiplier
    new_height = ratio_height * multiplier

    return new_width, new_height


def is_effectively_fully_opaque(image: Image.Image) -> tuple[bool, int | None]:
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    alpha = image.getchannel("A")
    alpha_min, alpha_max = alpha.getextrema()

    if alpha_min != alpha_max:
        return False, None

    if alpha_min in (128, 255):
        return True, alpha_min

    return False, None


def paste_edge_extended_padding(
    result: Image.Image,
    source_image: Image.Image,
    offset_x: int,
    offset_y: int,
) -> None:
    source_width = source_image.width
    source_height = source_image.height
    result_width = result.width
    result_height = result.height

    left_pad = offset_x
    top_pad = offset_y
    right_pad = result_width - source_width - offset_x
    bottom_pad = result_height - source_height - offset_y

    if top_pad > 0:
        top_strip = source_image.crop((0, 0, source_width, 1))
        top_fill = top_strip.resize((source_width, top_pad), Image.Resampling.NEAREST)
        result.paste(top_fill, (offset_x, 0))

    if bottom_pad > 0:
        bottom_strip = source_image.crop((0, source_height - 1, source_width, source_height))
        bottom_fill = bottom_strip.resize((source_width, bottom_pad), Image.Resampling.NEAREST)
        result.paste(bottom_fill, (offset_x, offset_y + source_height))

    if left_pad > 0:
        left_strip = source_image.crop((0, 0, 1, source_height))
        left_fill = left_strip.resize((left_pad, source_height), Image.Resampling.NEAREST)
        result.paste(left_fill, (0, offset_y))

    if right_pad > 0:
        right_strip = source_image.crop((source_width - 1, 0, source_width, source_height))
        right_fill = right_strip.resize((right_pad, source_height), Image.Resampling.NEAREST)
        result.paste(right_fill, (offset_x + source_width, offset_y))

    if left_pad > 0 and top_pad > 0:
        top_left_pixel = source_image.crop((0, 0, 1, 1))
        top_left_fill = top_left_pixel.resize((left_pad, top_pad), Image.Resampling.NEAREST)
        result.paste(top_left_fill, (0, 0))

    if right_pad > 0 and top_pad > 0:
        top_right_pixel = source_image.crop((source_width - 1, 0, source_width, 1))
        top_right_fill = top_right_pixel.resize((right_pad, top_pad), Image.Resampling.NEAREST)
        result.paste(top_right_fill, (offset_x + source_width, 0))

    if left_pad > 0 and bottom_pad > 0:
        bottom_left_pixel = source_image.crop((0, source_height - 1, 1, source_height))
        bottom_left_fill = bottom_left_pixel.resize((left_pad, bottom_pad), Image.Resampling.NEAREST)
        result.paste(bottom_left_fill, (0, offset_y + source_height))

    if right_pad > 0 and bottom_pad > 0:
        bottom_right_pixel = source_image.crop(
            (source_width - 1, source_height - 1, source_width, source_height)
        )
        bottom_right_fill = bottom_right_pixel.resize(
            (right_pad, bottom_pad),
            Image.Resampling.NEAREST,
        )
        result.paste(bottom_right_fill, (offset_x + source_width, offset_y + source_height))


def pad_image_to_size_centered(
    source_image: Image.Image,
    new_width: int,
    new_height: int,
) -> tuple[Image.Image, str]:
    offset_x = (new_width - source_image.width) // 2
    offset_y = (new_height - source_image.height) // 2

    is_opaque, opaque_alpha = is_effectively_fully_opaque(source_image)

    if is_opaque:
        result = Image.new("RGBA", (new_width, new_height), (0, 0, 0, opaque_alpha or 255))
        paste_edge_extended_padding(result, source_image, offset_x, offset_y)
        result.paste(source_image, (offset_x, offset_y))
        return result, f"edge-extended opaque padding (alpha={opaque_alpha})"

    result = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    result.paste(source_image, (offset_x, offset_y))
    return result, "transparent padding"


def save_png(path: Path, image: Image.Image) -> None:
    image.save(path, format="PNG", optimize=False)


def main() -> None:
    if not SOURCE_DIR.is_dir():
        print(f"ERROR: SOURCE_DIR does not exist:\n{SOURCE_DIR}")
        pause_and_exit(1)

    if not COMPARE_ROOT.is_dir():
        print(f"ERROR: COMPARE_ROOT does not exist:\n{COMPARE_ROOT}")
        pause_and_exit(1)

    source_pngs = sorted(SOURCE_DIR.glob("*.png"))

    if not source_pngs:
        print(f"ERROR: No PNG files found in:\n{SOURCE_DIR}")
        pause_and_exit(1)

    compare_map, duplicate_log_lines = build_compare_map(COMPARE_ROOT)

    lines: list[str] = []
    lines.append(f"Source folder: {SOURCE_DIR}")
    lines.append(f"Compare root: {COMPARE_ROOT}")
    lines.append("")
    lines.append(f"Total source PNGs: {len(source_pngs)}")
    lines.append("")

    matched = 0
    padded = 0
    already_matching_aspect = 0
    missing = 0
    errors = 0

    for source_path in source_pngs:
        compare_path = compare_map.get(source_path.name.lower())

        if compare_path is None:
            missing += 1
            lines.append(f"[MISSING] {source_path.name}")
            lines.append(f"  Source:  {source_path}")
            lines.append("  Compare: NOT FOUND")
            lines.append("")
            continue

        matched += 1

        try:
            source_width, source_height = get_image_size(source_path)
        except Exception as exc:
            errors += 1
            lines.append(f"[ERROR] {source_path.name}")
            lines.append(f"  Failed reading source image: {source_path}")
            lines.append(f"  Error: {exc}")
            lines.append("")
            continue

        try:
            compare_width, compare_height = get_image_size(compare_path)
        except Exception as exc:
            errors += 1
            lines.append(f"[ERROR] {source_path.name}")
            lines.append(f"  Failed reading compare image: {compare_path}")
            lines.append(f"  Error: {exc}")
            lines.append("")
            continue

        if same_aspect_ratio(
            source_width,
            source_height,
            compare_width,
            compare_height,
        ):
            already_matching_aspect += 1
            continue

        try:
            source_image = load_rgba(source_path)

            new_width, new_height = get_minimum_padded_size_for_target_aspect(
                source_width,
                source_height,
                compare_width,
                compare_height,
            )

            padded_image, padding_mode = pad_image_to_size_centered(
                source_image,
                new_width,
                new_height,
            )

            save_png(source_path, padded_image)

            padded += 1
            lines.append(f"[PADDED] {source_path.name}")
            lines.append(f"  Mode:      {padding_mode}")
            lines.append(f"  Source old: {source_path} -> {source_width}x{source_height}")
            lines.append(f"  Compare:    {compare_path} -> {compare_width}x{compare_height}")
            lines.append(f"  Source new: {source_path} -> {new_width}x{new_height}")
            lines.append("")

        except Exception as exc:
            errors += 1
            lines.append(f"[ERROR] {source_path.name}")
            lines.append(f"  Failed padding source image: {source_path}")
            lines.append(f"  Error: {exc}")
            lines.append("")

    lines.append("SUMMARY")
    lines.append(f"  Matched filenames:        {matched}")
    lines.append(f"  Padded:                  {padded}")
    lines.append(f"  Already matching aspect: {already_matching_aspect}")
    lines.append(f"  Missing compare files:   {missing}")
    lines.append(f"  Errors:                  {errors}")
    lines.append("")

    if duplicate_log_lines:
        lines.append("")
        lines.extend(duplicate_log_lines)

    try:
        LOG_FILE.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    except Exception as exc:
        print(f"ERROR: Failed to write log file:\n{LOG_FILE}\n\n{exc}")
        pause_and_exit(1)

    print(f"Done. Log written to:\n{LOG_FILE}")


if __name__ == "__main__":
    main()