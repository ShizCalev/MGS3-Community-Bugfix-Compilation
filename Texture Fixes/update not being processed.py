from __future__ import annotations

import os
from pathlib import Path


# ==========================================================
# CONFIG
# ==========================================================
ROOT_DIRS = [
    Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\mc textures"),
    Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\ps2 textures"),
    Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\Texture Fixes\Self Remade\Finalized"),
]

TARGET_FILENAME = "folders to process.txt"
SKIP_FILENAME = "folders to skip checking.txt"
OUTPUT_FILENAME = "not being processed.txt"
VALID_EXTENSIONS = {".png", ".tga"}

ROOT_SEPARATOR = "\n\n\n---------------------------------------------------------------------\n\n\n"


# ==========================================================
# HELPERS
# ==========================================================
def normalize_path(path_str: str) -> str:
    return os.path.normcase(os.path.normpath(path_str.strip()))


def folder_has_target_files(filenames: list[str]) -> bool:
    for filename in filenames:
        if Path(filename).suffix.lower() in VALID_EXTENSIONS:
            return True
    return False


def get_group_keys(root: Path, dirpath: str) -> tuple[str, str]:
    rel = Path(dirpath).relative_to(root)
    parts = rel.parts

    if len(parts) == 0:
        immediate_key = normalize_path(str(root))
        return immediate_key, immediate_key

    immediate_actual = root / parts[0]
    immediate_key = normalize_path(str(immediate_actual))

    if "self remade" in normalize_path(str(root)):
        return immediate_key, immediate_key

    if len(parts) >= 2:
        subgroup_actual = root / parts[0] / parts[1]
        subgroup_key = normalize_path(str(subgroup_actual))
        return immediate_key, subgroup_key

    return immediate_key, immediate_key


def get_folders_grouped_by_root(root: Path) -> dict[str, dict[str, list[tuple[str, str]]]]:
    grouped: dict[str, dict[str, list[tuple[str, str]]]] = {}

    for dirpath, _, filenames in os.walk(root):
        if not folder_has_target_files(filenames):
            continue

        actual_path = str(Path(dirpath))
        normalized_path = normalize_path(actual_path)

        immediate_key, subgroup_key = get_group_keys(root, dirpath)

        grouped.setdefault(immediate_key, {})
        grouped[immediate_key].setdefault(subgroup_key, [])
        grouped[immediate_key][subgroup_key].append((normalized_path, actual_path))

    return grouped


def read_nonempty_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def read_optional_nonempty_lines(path: Path) -> list[str]:
    if not path.exists():
        return []

    return read_nonempty_lines(path)


def write_text_if_changed(path: Path, content: str) -> None:
    if path.exists():
        old_content = path.read_text(encoding="utf-8")
        if old_content == content:
            return

    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(content, encoding="utf-8", newline="\n")
    tmp_path.replace(path)


def is_flatlist_win(txt_path: Path) -> bool:
    return "flatlist\\_win" in normalize_path(str(txt_path))


def is_ovr_win(txt_path: Path) -> bool:
    norm = normalize_path(str(txt_path))
    parts = [part for part in Path(norm).parts]

    for i in range(len(parts) - 3):
        if parts[i] != "flatlist":
            continue
        if parts[i + 1] != "ovr_stm":
            continue
        if not parts[i + 2].startswith("ovr_"):
            continue
        if parts[i + 3] != "_win":
            continue
        return True

    return False


# ==========================================================
# MAIN
# ==========================================================
def main() -> None:
    script_root = Path.cwd()

    all_grouped: dict[Path, dict[str, dict[str, list[tuple[str, str]]]]] = {}

    for root in ROOT_DIRS:
        if root.exists():
            all_grouped[root] = get_folders_grouped_by_root(root)
        else:
            all_grouped[root] = {}

    for txt_path in script_root.rglob(TARGET_FILENAME):
        processed_lines = read_nonempty_lines(txt_path)

        skip_path = txt_path.parent / SKIP_FILENAME
        skipped_lines = read_optional_nonempty_lines(skip_path)

        excluded_set = {
            normalize_path(line)
            for line in processed_lines + skipped_lines
        }

        flatlist_mode = is_flatlist_win(txt_path)
        ovr_mode = is_ovr_win(txt_path)

        root_chunks: list[str] = []

        for root in ROOT_DIRS:
            root_norm = normalize_path(str(root))

            if ovr_mode:
                if "self remade" not in root_norm:
                    continue
            else:
                if flatlist_mode and "self remade" in root_norm:
                    continue

            immediate_groups = all_grouped.get(root, {})
            immediate_chunks: list[str] = []

            for immediate_key in sorted(immediate_groups.keys()):
                subgroup_map = immediate_groups[immediate_key]
                subgroup_chunks: list[str] = []

                for subgroup_key in sorted(subgroup_map.keys()):
                    entries = sorted(subgroup_map[subgroup_key], key=lambda x: x[0])

                    filtered_actual_paths: list[str] = []

                    for normalized_path, actual_path in entries:
                        if normalized_path in excluded_set:
                            continue

                        if (
                            flatlist_mode
                            and not ovr_mode
                            and "ps2 textures" in root_norm
                            and "bp_remade" in normalize_path(actual_path)
                        ):
                            continue

                        filtered_actual_paths.append(actual_path)

                    if not filtered_actual_paths:
                        continue

                    subgroup_chunks.append("\n".join(filtered_actual_paths))

                if not subgroup_chunks:
                    continue

                if "self remade" in root_norm:
                    immediate_chunks.append("\n".join(subgroup_chunks))
                else:
                    immediate_chunks.append("\n\n".join(subgroup_chunks))

            if not immediate_chunks:
                continue

            root_chunks.append("\n\n".join(immediate_chunks))

        content = ""
        if root_chunks:
            content = ROOT_SEPARATOR.join(root_chunks) + "\n"

        output_path = txt_path.parent / OUTPUT_FILENAME
        write_text_if_changed(output_path, content)


if __name__ == "__main__":
    main()