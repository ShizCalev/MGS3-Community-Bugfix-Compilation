from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

INPUT_FILENAMES = (
    "StringDB - Cutscenes.xml",
    "StringDB - GCX.xml",
    "StringDB - Radio.xml",
)

OUTPUT_FILENAME = "StringDB.xml"


@dataclass
class MergedString:
    lang: int
    text: str
    file_refs: list[tuple[int, int]] = field(default_factory=list)
    seen_file_refs: set[tuple[int, int]] = field(default_factory=set)


def normalize_lf(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def merge_language(existing: int, incoming: int) -> int:
    if existing == incoming:
        return existing
    if existing == -1:
        return incoming
    if incoming == -1:
        return existing
    return -1


def parse_int(value: str, context: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValueError(f"{context}: invalid integer {value!r}") from exc


def merge_databases(root: Path) -> ET.ElementTree:
    output_root = ET.Element("StringDB")
    merged_strings: OrderedDict[str, MergedString] = OrderedDict()

    next_file_id = 0

    for input_filename in INPUT_FILENAMES:
        input_path = root / input_filename
        if not input_path.is_file():
            raise FileNotFoundError(f"Missing input file: {input_path}")

        tree = ET.parse(input_path)
        source_root = tree.getroot()

        if source_root.tag != "StringDB":
            raise ValueError(
                f"{input_path}: expected root element <StringDB>, "
                f"found <{source_root.tag}>"
            )

        file_id_map: dict[int, int] = {}

        for file_element in source_root.findall("File"):
            old_file_id = parse_int(
                file_element.attrib["id"],
                f"{input_path}: <File id>",
            )
            new_file_id = next_file_id
            next_file_id += 1
            file_id_map[old_file_id] = new_file_id

            new_file_element = ET.SubElement(
                output_root,
                "File",
                {
                    "id": str(new_file_id),
                    "stringCount": file_element.attrib.get("stringCount", "0"),
                },
            )
            new_file_element.text = normalize_lf(file_element.text)

        for string_element in source_root.findall("String"):
            hash_value = string_element.attrib.get("hash")
            if not hash_value:
                raise ValueError(f"{input_path}: <String> is missing hash")

            lang = parse_int(
                string_element.attrib.get("lang", "-1"),
                f"{input_path}: <String lang>",
            )

            text_element = string_element.find("Text")
            if text_element is None:
                raise ValueError(
                    f"{input_path}: hash {hash_value} is missing <Text>"
                )

            text = normalize_lf(text_element.text)
            merged = merged_strings.get(hash_value)

            if merged is None:
                merged = MergedString(
                    lang=lang,
                    text=text,
                )
                merged_strings[hash_value] = merged
            else:
                if merged.text != text:
                    raise ValueError(
                        f"Hash collision for {hash_value}:\n"
                        f"First text: {merged.text!r}\n"
                        f"Other text: {text!r}\n"
                        f"Source: {input_path}"
                    )

                merged.lang = merge_language(merged.lang, lang)

            for file_ref_element in string_element.findall("FileRef"):
                old_ref_id = parse_int(
                    file_ref_element.attrib["id"],
                    f"{input_path}: <FileRef id>",
                )

                if old_ref_id not in file_id_map:
                    raise ValueError(
                        f"{input_path}: hash {hash_value} references "
                        f"unknown file id {old_ref_id}"
                    )

                idx = parse_int(
                    file_ref_element.attrib["idx"],
                    f"{input_path}: <FileRef idx>",
                )
                file_ref = (file_id_map[old_ref_id], idx)

                if file_ref not in merged.seen_file_refs:
                    merged.seen_file_refs.add(file_ref)
                    merged.file_refs.append(file_ref)

    for hash_value, merged in merged_strings.items():
        string_element = ET.SubElement(
            output_root,
            "String",
            {
                "lang": str(merged.lang),
                "hash": hash_value,
            },
        )

        text_element = ET.SubElement(string_element, "Text")
        text_element.text = merged.text

        for file_id, idx in merged.file_refs:
            ET.SubElement(
                string_element,
                "FileRef",
                {
                    "id": str(file_id),
                    "idx": str(idx),
                },
            )

    tree = ET.ElementTree(output_root)
    ET.indent(tree, space="  ")
    return tree


def main() -> int:
    root = Path(__file__).resolve().parent
    output_path = root / OUTPUT_FILENAME

    try:
        tree = merge_databases(root)

        xml_bytes = ET.tostring(
            tree.getroot(),
            encoding="utf-8",
            xml_declaration=False,
            short_empty_elements=True,
        )
        xml_bytes = xml_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        output_path.write_bytes(xml_bytes + b"\n")
    except (OSError, ET.ParseError, KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    file_count = len(tree.getroot().findall("File"))
    string_count = len(tree.getroot().findall("String"))

    print(f"Wrote: {output_path}")
    print(f"Files: {file_count}")
    print(f"Unique hashes: {string_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())