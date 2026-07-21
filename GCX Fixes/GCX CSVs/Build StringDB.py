from __future__ import annotations

import csv
import sys
import zlib
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

OUTPUT_FILENAME = "StringDB.xml"
TEXT_COLUMN = 2

EXCLUDED_FILENAMES: set[str] = set()

LANGUAGE_IDS = {
    "gr": 3,
    "it": 4,
    "jp": 7,
    "sp": 5,
}

FR_SHARED_LANG = -1
FR_ENGLISH_LANG = 1
FR_FRENCH_LANG = 2
FR_REFERENCE_FOLDERS = ("gr", "it", "sp")

FR_SHARED_COUNT_OVERRIDES = {
    "_bp/scenerio_stage_title.csv": 1568,
}


@dataclass
class StringEntry:
    lang: int
    text: str
    hash_value: str
    file_refs: list[tuple[int, int]] = field(default_factory=list)


def string_hash(text: str) -> str:
    crc32 = zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF
    return f"0x{crc32:08x}"


def parse_offset(value: str, csv_path: Path, row_number: int) -> int:
    value = value.strip()

    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValueError(
            f"{csv_path}: row {row_number}: invalid offset {value!r}"
        ) from exc


def read_csv(csv_path: Path) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)

        for row_number, row in enumerate(reader, start=1):
            if not row or all(not value.strip() for value in row):
                continue

            if len(row) <= TEXT_COLUMN:
                raise ValueError(
                    f"{csv_path}: row {row_number}: expected at least "
                    f"{TEXT_COLUMN + 1} columns, found {len(row)}"
                )

            offset = parse_offset(row[0], csv_path, row_number)
            text = row[TEXT_COLUMN].replace("\r\n", "\n").replace("\r", "\n")
            rows.append((offset, text))

    return rows


def collect_csv_files(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() == ".csv"
            and path.parent != root
            and path.name.lower() not in EXCLUDED_FILENAMES
        ),
        key=lambda path: path.relative_to(root).as_posix().lower(),
    )


def top_level_folder(relative_path: Path) -> str:
    return relative_path.parts[0].lower() if relative_path.parts else ""


def matching_reference_counts(
    root: Path,
    relative_fr_path: Path,
    row_cache: dict[Path, list[tuple[int, str]]],
) -> list[int]:
    counts: list[int] = []
    relative_without_language = Path(*relative_fr_path.parts[1:])

    for folder in FR_REFERENCE_FOLDERS:
        candidate = root / folder / relative_without_language

        if candidate.is_file():
            rows = row_cache.get(candidate)
            if rows is None:
                rows = read_csv(candidate)
                row_cache[candidate] = rows
            counts.append(len(rows))

    return counts


FRENCH_MARKERS = {
    "à", "afin", "ainsi", "alors", "appuyez", "avec", "avoir", "cette",
    "comme", "dans", "des", "du", "elle", "en", "est", "et", "être",
    "faire", "fois", "il", "j'ai", "la", "le", "les", "leur", "mais", "ne",
    "oiseau", "ou", "par", "pas", "peut", "plus", "pour", "que", "qui",
    "sans", "semble", "son", "sur", "très", "une", "utiliser", "vous",
}

ENGLISH_MARKERS = {
    "a", "and", "are", "as", "at", "be", "body", "button", "can",
    "bird", "for", "from", "has", "have", "in", "is", "it", "looks",
    "native", "not", "of", "on", "or", "press", "seems", "the", "this",
    "to", "told", "tried", "use", "useful", "very", "with", "you", "your",
}


def language_scores(text: str) -> tuple[int, int]:
    lowered = text.casefold()
    words = {
        word.strip(".,:;!?()[]{}<>\"'…-–—")
        for word in lowered.replace("\n", " ").split()
    }
    french = sum(word in FRENCH_MARKERS for word in words)
    english = sum(word in ENGLISH_MARKERS for word in words)
    french += sum(lowered.count(char) for char in "àâçéèêëîïôùûüÿœæ") * 3
    return french, english


def classify_language(text: str) -> int:
    stripped = text.strip()

    if not stripped or stripped == "END":
        return FR_SHARED_LANG

    french, english = language_scores(text)

    if french > english:
        return FR_FRENCH_LANG

    if english > french:
        return FR_ENGLISH_LANG

    return FR_SHARED_LANG


def classify_fr_group(rows: list[tuple[int, str]]) -> list[int]:
    direct = [classify_language(text) for _, text in rows]

    french_votes = sum(lang == FR_FRENCH_LANG for lang in direct)
    english_votes = sum(lang == FR_ENGLISH_LANG for lang in direct)

    if french_votes > english_votes:
        fallback = FR_FRENCH_LANG
    elif english_votes > french_votes:
        fallback = FR_ENGLISH_LANG
    else:
        fallback = FR_SHARED_LANG

    return [fallback if lang == FR_SHARED_LANG else lang for lang in direct]


def classify_fr_tail(rows: list[tuple[int, str]]) -> list[int]:
    languages = [FR_SHARED_LANG] * len(rows)
    group_start = 0

    for index, (_, text) in enumerate(rows):
        if text.strip() != "END":
            continue

        group_languages = classify_fr_group(rows[group_start:index])
        languages[group_start:index] = group_languages
        languages[index] = FR_SHARED_LANG
        group_start = index + 1

    if group_start < len(rows):
        languages[group_start:] = classify_fr_group(rows[group_start:])

    return languages


def split_fr_languages(
    root: Path,
    relative_fr_path: Path,
    fr_rows: list[tuple[int, str]],
    row_cache: dict[Path, list[tuple[int, str]]],
) -> list[int]:
    fr_row_count = len(fr_rows)
    reference_counts = matching_reference_counts(
        root,
        relative_fr_path,
        row_cache,
    )

    if not reference_counts:
        raise ValueError(
            f"{relative_fr_path}: no matching gr, it, or sp CSV was found "
            "to determine the shared prefix"
        )

    relative_without_language = Path(*relative_fr_path.parts[1:]).as_posix()
    shared_count = FR_SHARED_COUNT_OVERRIDES.get(relative_without_language)

    if shared_count is None:
        single_language_count = Counter(reference_counts).most_common(1)[0][0]
        shared_count = (2 * single_language_count) - fr_row_count

    if shared_count < 0 or shared_count > fr_row_count:
        raise ValueError(
            f"{relative_fr_path}: invalid shared prefix calculated from "
            f"fr={fr_row_count} and reference counts={reference_counts}"
        )

    tail_languages = classify_fr_tail(fr_rows[shared_count:])
    return [FR_SHARED_LANG] * shared_count + tail_languages


def row_languages(
    root: Path,
    relative_path: Path,
    rows: list[tuple[int, str]],
    row_cache: dict[Path, list[tuple[int, str]]],
) -> list[int]:
    folder = top_level_folder(relative_path)

    if folder == "fr":
        return split_fr_languages(root, relative_path, rows, row_cache)

    return [LANGUAGE_IDS.get(folder, -1)] * len(rows)


def build_string_db(root: Path, csv_files: list[Path]) -> ET.ElementTree:
    root_element = ET.Element("StringDB")
    strings: OrderedDict[str, StringEntry] = OrderedDict()
    row_cache: dict[Path, list[tuple[int, str]]] = {}

    for file_id, csv_path in enumerate(csv_files):
        rows = row_cache.get(csv_path)
        if rows is None:
            rows = read_csv(csv_path)
            row_cache[csv_path] = rows

        relative_csv_path = csv_path.relative_to(root)
        languages = row_languages(
            root,
            relative_csv_path,
            rows,
            row_cache,
        )
        relative_path = relative_csv_path.with_suffix("").as_posix()
        file_element = ET.SubElement(
            root_element,
            "File",
            {
                "id": str(file_id),
                "stringCount": str(len(rows)),
            },
        )
        file_element.text = relative_path

        for (offset, text), lang in zip(rows, languages, strict=True):
            hash_value = string_hash(text)
            entry = strings.get(hash_value)

            if entry is None:
                entry = StringEntry(
                    lang=lang,
                    text=text,
                    hash_value=hash_value,
                )
                strings[hash_value] = entry
            else:
                if entry.text != text:
                    raise ValueError(
                        f"CRC32 collision detected for hash {hash_value}: "
                        f"{entry.text!r} != {text!r}"
                    )

                if entry.lang == FR_SHARED_LANG and lang != FR_SHARED_LANG:
                    entry.lang = lang
                elif (
                    lang != FR_SHARED_LANG
                    and entry.lang != FR_SHARED_LANG
                    and entry.lang != lang
                ):
                    entry.lang = FR_SHARED_LANG

            entry.file_refs.append((file_id, offset))

    for entry in strings.values():
        string_element = ET.SubElement(
            root_element,
            "String",
            {
                "lang": str(entry.lang),
                "hash": entry.hash_value,
            },
        )

        text_element = ET.SubElement(string_element, "Text")
        text_element.text = entry.text

        for file_id, offset in entry.file_refs:
            ET.SubElement(
                string_element,
                "FileRef",
                {
                    "id": str(file_id),
                    "idx": str(offset),
                },
            )

    tree = ET.ElementTree(root_element)
    ET.indent(tree, space="  ")
    return tree


def main() -> int:
    root = Path(__file__).resolve().parent
    output_path = root / OUTPUT_FILENAME
    csv_files = collect_csv_files(root)

    if not csv_files:
        print(
            "No CSV files were found below the script directory.\n"
            "CSV files directly beside the script are intentionally skipped.",
            file=sys.stderr,
        )
        return 1

    try:
        tree = build_string_db(root, csv_files)
        xml_bytes = ET.tostring(
            tree.getroot(),
            encoding="utf-8",
            xml_declaration=False,
            short_empty_elements=True,
        )
        xml_bytes = xml_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        output_path.write_bytes(xml_bytes + b"\n")
    except (OSError, csv.Error, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {output_path}")
    print(f"Files: {len(csv_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())