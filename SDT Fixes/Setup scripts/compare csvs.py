from __future__ import annotations

import csv
import hashlib
from pathlib import Path


CSV_A = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\better_audio_scripts\_csv_sha1s.csv"
)
CSV_B = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\original_subtitles\_csv_sha1s.csv"
)

ROOT_A = CSV_A.parent
ROOT_B = CSV_B.parent

OUTPUT_MATCHES = Path(__file__).resolve().parent / "csv_sha1_matches.csv"
OUTPUT_MISMATCHES = Path(__file__).resolve().parent / "csv_sha1_mismatches.csv"
OUTPUT_UNIQUES = Path(__file__).resolve().parent / "csv_sha1_unique_entries.csv"

SHA1_BUFFER_SIZE = 8 * 1024 * 1024


def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(SHA1_BUFFER_SIZE), b""):
            h.update(chunk)

    return h.hexdigest()


def is_trivial_csv(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    if not normalized:
        return True

    lines = normalized.split("\n")

    if len(lines) == 1 and lines[0].strip() == "Start Time,End Time,Lang ID,Text":
        return True

    try:
        reader = csv.DictReader(lines)
    except Exception:
        return False

    if reader.fieldnames is None:
        return False

    if "Text" not in reader.fieldnames:
        return False

    has_any_text = False

    for row in reader:
        text_value = (row.get("Text") or "").strip()

        if text_value:
            has_any_text = True
            break

    return not has_any_text


def delete_trivial_csvs(root: Path) -> int:
    deleted = 0

    for path in sorted(root.rglob("*.csv"), key=lambda p: str(p).lower()):
        if path.name.lower() == "_csv_sha1s.csv":
            continue

        if not path.is_file():
            continue

        if is_trivial_csv(path):
            path.unlink()
            deleted += 1
            print(f"[DELETED TRIVIAL CSV] {path}")

    return deleted


def update_manifests(root: Path) -> int:
    updated = 0

    for manifest_path in sorted(root.rglob("manifest.txt"), key=lambda p: str(p).lower()):
        folder = manifest_path.parent
        csv_names = sorted(
            [
                child.name
                for child in folder.iterdir()
                if child.is_file()
                and child.suffix.lower() == ".csv"
                and child.name.lower() != "_csv_sha1s.csv"
            ],
            key=str.lower,
        )

        content = "\n".join(csv_names)
        if content:
            content += "\n"

        existing = ""
        if manifest_path.exists():
            existing = manifest_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")

        if existing == content:
            continue

        manifest_path.write_text(content, encoding="utf-8", newline="\n")
        updated += 1
        print(f"[UPDATED MANIFEST] {manifest_path}")

    return updated


def rebuild_sha1_csv(index_path: Path) -> int:
    root = index_path.parent
    rows: list[tuple[str, str]] = []

    for path in sorted(root.rglob("*.csv"), key=lambda p: str(p).lower()):
        if path.name.lower() == "_csv_sha1s.csv":
            continue

        relative_csv_path = path.relative_to(root).as_posix()
        original_sha1 = sha1_of_file(path)
        rows.append((relative_csv_path, original_sha1))

    rows.sort(key=lambda r: r[0].lower())

    with index_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["relative_csv_path", "original_sha1"])
        writer.writerows(rows)

    print(f"[UPDATED SHA1 CSV] {index_path} ({len(rows)} rows)")
    return len(rows)


def load_sha1_csv(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError(f"Missing header row in {path}")

        required = {"relative_csv_path", "original_sha1"}
        if not required.issubset(reader.fieldnames):
            raise ValueError(f"Invalid CSV headers in {path}")

        for row in reader:
            relative_csv_path = row["relative_csv_path"].strip()
            original_sha1 = row["original_sha1"].strip().lower()

            if not relative_csv_path:
                continue

            rows[relative_csv_path] = original_sha1

    return rows


def delete_matching_better_audio_csvs(
    root_a: Path,
    a_rows: dict[str, str],
    b_rows: dict[str, str],
) -> int:
    deleted = 0

    shared_paths = sorted(set(a_rows) & set(b_rows), key=str.lower)

    for relative_csv_path in shared_paths:
        a_sha1 = a_rows[relative_csv_path]
        b_sha1 = b_rows[relative_csv_path]

        if a_sha1 != b_sha1:
            continue

        target_path = root_a / Path(relative_csv_path)

        if not target_path.is_file():
            continue

        target_path.unlink()
        deleted += 1
        print(f"[DELETED DUPLICATE BETTER_AUDIO CSV] {target_path}")

    return deleted


def cleanup_empty_better_audio_dirs(root: Path) -> int:
    removed = 0

    all_dirs = sorted(
        [p for p in root.rglob("*") if p.is_dir()],
        key=lambda p: len(p.parts),
        reverse=True,
    )

    for folder in all_dirs:
        entries = list(folder.iterdir())

        if not entries:
            folder.rmdir()
            removed += 1
            print(f"[REMOVED EMPTY DIR] {folder}")
            continue

        if all(
            p.is_file() and p.name.lower() == "_csv_sha1s.csv"
            for p in entries
        ):
            for p in entries:
                p.unlink()

            folder.rmdir()
            removed += 1
            print(f"[REMOVED DIR WITH ONLY SHA1 CSV] {folder}")

    return removed


def write_csv_if_has_rows(
    path: Path,
    header: list[str],
    rows: list[tuple[str, ...]],
) -> None:
    if not rows:
        if path.exists():
            path.unlink()
            print(f"[REMOVED] {path}")
        return

    rows.sort(key=lambda r: r[0].lower())

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)

    print(f"[WROTE] {path} ({len(rows)} rows)")


def main() -> None:
    deleted_trivial_a = delete_trivial_csvs(ROOT_A)
    deleted_trivial_b = delete_trivial_csvs(ROOT_B)

    updated_manifests_a = update_manifests(ROOT_A)
    updated_manifests_b = update_manifests(ROOT_B)

    rebuild_sha1_csv(CSV_A)
    rebuild_sha1_csv(CSV_B)

    a_rows = load_sha1_csv(CSV_A)
    b_rows = load_sha1_csv(CSV_B)

    deleted_duplicates = delete_matching_better_audio_csvs(ROOT_A, a_rows, b_rows)

    if deleted_duplicates:
        updated_manifests_a += update_manifests(ROOT_A)
        rebuild_sha1_csv(CSV_A)
        rebuild_sha1_csv(CSV_B)
        a_rows = load_sha1_csv(CSV_A)
        b_rows = load_sha1_csv(CSV_B)

    removed_dirs = cleanup_empty_better_audio_dirs(ROOT_A)

    if removed_dirs:
        updated_manifests_a += update_manifests(ROOT_A)
        rebuild_sha1_csv(CSV_A)
        a_rows = load_sha1_csv(CSV_A)

    shared_paths = sorted(set(a_rows) & set(b_rows), key=str.lower)
    a_only_paths = sorted(set(a_rows) - set(b_rows), key=str.lower)
    b_only_paths = sorted(set(b_rows) - set(a_rows), key=str.lower)

    matches: list[tuple[str, str]] = []
    mismatches: list[tuple[str, str, str]] = []
    uniques: list[tuple[str, str, str]] = []

    for relative_csv_path in shared_paths:
        a_sha1 = a_rows[relative_csv_path]
        b_sha1 = b_rows[relative_csv_path]

        if a_sha1 == b_sha1:
            matches.append((relative_csv_path, a_sha1))
        else:
            mismatches.append((relative_csv_path, a_sha1, b_sha1))

    for relative_csv_path in a_only_paths:
        uniques.append(
            (
                relative_csv_path,
                "better_audio_scripts",
                a_rows[relative_csv_path],
            )
        )

    for relative_csv_path in b_only_paths:
        uniques.append(
            (
                relative_csv_path,
                "original_subtitles",
                b_rows[relative_csv_path],
            )
        )

    write_csv_if_has_rows(
        OUTPUT_MATCHES,
        [
            "relative_csv_path",
            "original_sha1",
        ],
        matches,
    )

    write_csv_if_has_rows(
        OUTPUT_MISMATCHES,
        [
            "relative_csv_path",
            "better_audio_scripts_original_sha1",
            "original_subtitles_original_sha1",
        ],
        mismatches,
    )

    write_csv_if_has_rows(
        OUTPUT_UNIQUES,
        [
            "relative_csv_path",
            "source",
            "original_sha1",
        ],
        uniques,
    )

    print(f"Deleted trivial CSVs: {deleted_trivial_a + deleted_trivial_b}")
    print(f"Deleted duplicate better_audio_scripts CSVs: {deleted_duplicates}")
    print(f"Removed empty better_audio_scripts dirs: {removed_dirs}")
    print(f"Updated manifests: {updated_manifests_a + updated_manifests_b}")
    print(f"{CSV_A.name} rows: {len(a_rows)}")
    print(f"{CSV_B.name} rows: {len(b_rows)}")
    print(f"Compared {len(shared_paths)} shared files.")
    print(f"Matches: {len(matches)}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"Unique entries: {len(uniques)}")


if __name__ == "__main__":
    main()