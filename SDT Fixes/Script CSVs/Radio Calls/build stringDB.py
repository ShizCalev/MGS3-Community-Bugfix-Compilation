from __future__ import annotations

import csv
import re
import sys
import zlib
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

OUTPUT_FILENAME = "StringDB.xml"

LANGUAGE_IDS = {
    "[ENG]": 1,
    "[FRE]": 2,
    "[GER]": 3,
    "[ITA]": 4,
    "[SPA]": 5,
    "[JPN]": 7,
}


JAPANESE_TEXT_PATTERN = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def resolve_language(lang_tag: str, text: str, csv_path: Path, row_number: int) -> int:
    if lang_tag == "[JPN]" or JAPANESE_TEXT_PATTERN.search(text):
        return 7

    if lang_tag not in LANGUAGE_IDS:
        raise ValueError(
            f"{csv_path}: row {row_number}: unknown Lang ID {lang_tag!r}"
        )

    return LANGUAGE_IDS[lang_tag]


@dataclass
class StringEntry:
    lang: int
    text: str
    hash_value: str
    file_refs: list[tuple[int, int]] = field(default_factory=list)


def normalize_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def string_hash(text: str) -> str:
    crc32 = zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF
    return f"0x{crc32:08x}"


def merge_language(existing: int, incoming: int) -> int:
    if existing == incoming:
        return existing
    if existing == -1:
        return incoming
    if incoming == -1:
        return existing
    return -1


def parse_offset(value: str, csv_path: Path, row_number: int) -> int:
    try:
        return int(value.strip(), 0)
    except ValueError as exc:
        raise ValueError(
            f"{csv_path}: row {row_number}: invalid Start Time {value!r}"
        ) from exc


def top_level_folder(root: Path, csv_path: Path) -> str:
    relative_path = csv_path.relative_to(root)
    return relative_path.parts[0].lower() if relative_path.parts else ""


def read_csv(root: Path, csv_path: Path) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    folder = top_level_folder(root, csv_path)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        required_columns = {"Start Time", "Lang ID", "Text"}
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path}: missing CSV header")

        missing_columns = required_columns.difference(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"{csv_path}: missing columns: {', '.join(sorted(missing_columns))}"
            )

        for row_number, row in enumerate(reader, start=2):
            if not row or all(not (value or "").strip() for value in row.values()):
                continue

            offset = parse_offset(row["Start Time"], csv_path, row_number)
            text = normalize_lf(row["Text"] or "")

            lang_tag = (row["Lang ID"] or "").strip().upper()
            lang = resolve_language(lang_tag, text, csv_path, row_number)

            rows.append((offset, lang, text))

    return rows


def collect_csv_files(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() == ".csv"
            and path.parent != root
        ),
        key=lambda path: path.relative_to(root).as_posix().lower(),
    )


def build_string_db(root: Path, csv_files: list[Path]) -> ET.ElementTree:
    root_element = ET.Element("StringDB")
    strings: OrderedDict[str, StringEntry] = OrderedDict()

    for file_id, csv_path in enumerate(csv_files):
        rows = read_csv(root, csv_path)
        relative_path = csv_path.relative_to(root).with_suffix("").as_posix()

        file_element = ET.SubElement(
            root_element,
            "File",
            {
                "id": str(file_id),
                "stringCount": str(len(rows)),
            },
        )
        file_element.text = relative_path

        for offset, lang, text in rows:
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

                entry.lang = merge_language(entry.lang, lang)

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
    print(f"Unique hashes: {len(tree.getroot().findall('String'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())