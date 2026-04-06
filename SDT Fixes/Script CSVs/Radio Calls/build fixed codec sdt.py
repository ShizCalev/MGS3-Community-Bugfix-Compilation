from __future__ import annotations

import csv
import hashlib
import os
import struct
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time

SCRIPT_DIR = Path(__file__).resolve().parent
SHA1_CSV = SCRIPT_DIR / "_csv_sha1s.csv"

GAME_ROOT = Path(r"G:\Steam\steamapps\common\MGS3")
OUTPUT_ROOT = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Fixed Codec")
OUTPUT_MANIFEST = OUTPUT_ROOT / "_fixed_codec_sha1s.csv"

MAX_WORKERS = max(4, os.cpu_count() or 4)
SHA1_BUFFER_SIZE = 8 * 1024 * 1024

HEX_DIGITS = set("0123456789abcdefABCDEF")


def wait_for_exit() -> None:
    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass


def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(SHA1_BUFFER_SIZE), b""):
            h.update(chunk)

    return h.hexdigest()


def enforce_lf_only(path: Path) -> None:
    with path.open("rb") as f:
        data = f.read()

    if b"\r\n" in data:
        raise ValueError("CRLF detected")

    if b"\r" in data:
        raise ValueError("CR detected")


def get_line_col(text: str, pos: int) -> tuple[int, int]:
    line = text.count("\n", 0, pos) + 1
    last_newline = text.rfind("\n", 0, pos)

    if last_newline == -1:
        col = pos + 1
    else:
        col = pos - last_newline

    return line, col


def parse_hex_array(text: str) -> set[str]:
    value = text.strip()

    if not value or value == "[]":
        return set()

    if not value.startswith("[") or not value.endswith("]"):
        raise ValueError(f"Invalid hex array format: {text!r}")

    inner = value[1:-1].strip()

    if not inner:
        return set()

    result: set[str] = set()

    for part in inner.split(","):
        hex_value = part.strip().lower()

        if not hex_value:
            continue

        if not hex_value.startswith("0x"):
            raise ValueError(f"Invalid hex value: {hex_value!r}")

        try:
            int(hex_value, 16)
        except ValueError as exc:
            raise ValueError(f"Invalid hex value: {hex_value!r}") from exc

        result.add(hex_value)

    return result


def format_hex_array(values: set[str]) -> str:
    if not values:
        return "[]"

    ordered = sorted(values, key=lambda value: int(value, 16))
    return "[" + ",".join(ordered) + "]"


def parse_quoted_field(text: str, pos: int, key: str, field_name: str) -> tuple[str, int]:
    if pos >= len(text) or text[pos] != '"':
        line, col = get_line_col(text, pos)
        raise ValueError(f"{key}: Expected opening quote for {field_name} at line {line}, column {col}")

    pos += 1
    chars: list[str] = []

    while pos < len(text):
        ch = text[pos]

        if ch == '"':
            if pos + 1 < len(text) and text[pos + 1] == '"':
                chars.append('"')
                pos += 2
                continue

            pos += 1
            return "".join(chars), pos

        chars.append(ch)
        pos += 1

    line, col = get_line_col(text, len(text))
    raise ValueError(f"{key}: Unterminated quoted field for {field_name} near line {line}, column {col}")


def parse_modified_csv_text(text: str) -> list[tuple[str, str]]:
    pos = 0
    seen_keys: set[str] = set()
    records: list[tuple[str, str]] = []

    while pos < len(text):
        while pos < len(text) and text[pos] == "\n":
            pos += 1

        if pos >= len(text):
            break

        key_start = pos

        if pos + 2 > len(text) or text[pos:pos + 2].lower() != "0x":
            line, col = get_line_col(text, pos)
            preview = text[pos:pos + 60].replace("\n", "\\n")
            raise ValueError(f"Malformed record start at line {line}, column {col}: {preview!r}")

        pos += 2

        hex_start = pos
        while pos < len(text) and text[pos] in HEX_DIGITS:
            pos += 1

        if pos == hex_start:
            line, col = get_line_col(text, pos)
            raise ValueError(f"Missing hex digits after 0x at line {line}, column {col}")

        key = text[key_start:pos].lower()

        if pos >= len(text) or text[pos] != ",":
            line, col = get_line_col(text, pos)
            raise ValueError(f"{key}: Expected comma after key at line {line}, column {col}")

        pos += 1

        if key in seen_keys:
            raise ValueError(f"{key}: Duplicate key")
        seen_keys.add(key)

        left_value, pos = parse_quoted_field(text, pos, key, "left field")

        if pos >= len(text) or text[pos] != ",":
            line, col = get_line_col(text, pos)
            preview = text[pos:pos + 60].replace("\n", "\\n")
            raise ValueError(
                f"{key}: Expected comma between duplicated fields at line {line}, column {col}: {preview!r}"
            )

        pos += 1

        right_value, pos = parse_quoted_field(text, pos, key, "right field")

        if left_value != right_value:
            raise ValueError(f"{key}: Duplicated fields do not match")

        records.append((key, left_value))

        if pos < len(text):
            if text[pos] == "\n":
                pos += 1
            elif text[pos:pos + 2].lower() == "0x":
                pass
            else:
                line, col = get_line_col(text, pos)
                preview = text[pos:pos + 60].replace("\n", "\\n")
                raise ValueError(
                    f"{key}: Expected newline, next key, or EOF after second field at line {line}, column {col}: {preview!r}"
                )

    return records


def read_modified_csv_records(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8-sig", newline="")
    return parse_modified_csv_text(text)


def scan_hexes_from_records(records: list[tuple[str, str]]) -> set[str]:
    return {key for key, _ in records}


def hash_worker(row: dict[str, str]) -> tuple[str, str, str, str | None]:
    rel_path = row.get("relative_csv_path", "").strip()

    if not rel_path:
        return "", "", "", "Missing relative_csv_path"

    csv_path = SCRIPT_DIR / Path(rel_path)

    if not csv_path.exists() or not csv_path.is_file():
        return rel_path, "", "", "Missing file"

    try:
        enforce_lf_only(csv_path)
    except Exception as exc:
        return rel_path, "", "", f"Line ending error: {exc}"

    try:
        actual_sha1 = sha1_of_file(csv_path)
    except Exception as exc:
        return rel_path, "", "", f"SHA1 error: {exc}"

    expected_sha1 = row.get("csv_sha1", "").strip().lower()
    return rel_path, expected_sha1, actual_sha1, None


def verify_sdt_worker(row: dict[str, str]) -> tuple[str, str | None]:
    rel_sdt_path = row.get("relative_sdt_path", "").strip()

    if not rel_sdt_path:
        return row.get("relative_csv_path", "").strip() or "<unknown>", "Missing relative_sdt_path"

    expected_sdt_sha1 = row.get("sdt_sha1", "").strip().lower()
    if not expected_sdt_sha1:
        return row.get("relative_csv_path", "").strip() or "<unknown>", "Missing expected sdt_sha1"

    sdt_path = GAME_ROOT / Path(rel_sdt_path)
    if not sdt_path.exists() or not sdt_path.is_file():
        return row.get("relative_csv_path", "").strip() or "<unknown>", f"Missing source SDT: {sdt_path}"

    try:
        actual_sdt_sha1 = sha1_of_file(sdt_path)
    except Exception as exc:
        return row.get("relative_csv_path", "").strip() or "<unknown>", f"SDT SHA1 error: {exc}"

    if actual_sdt_sha1 != expected_sdt_sha1:
        return (
            row.get("relative_csv_path", "").strip() or "<unknown>",
            f"SDT SHA1 mismatch | relative_sdt_path={rel_sdt_path} | expected={expected_sdt_sha1} | actual={actual_sdt_sha1}",
        )

    return row.get("relative_csv_path", "").strip() or "<unknown>", None


def verify_changed_file(row: dict[str, str]) -> tuple[str, list[str], list[tuple[str, str]] | None]:
    rel_path = row["relative_csv_path"].strip()
    csv_path = SCRIPT_DIR / Path(rel_path)

    try:
        expected_hexes = parse_hex_array(row.get("hex_values", "[]"))
    except Exception as exc:
        return rel_path, [f"Invalid hex_values: {exc}"], None

    try:
        records = read_modified_csv_records(csv_path)
    except Exception as exc:
        return rel_path, [str(exc)], None

    actual_hexes = scan_hexes_from_records(records)

    errors: list[str] = []

    missing = expected_hexes - actual_hexes
    extra = actual_hexes - expected_hexes

    if missing or extra:
        parts: list[str] = []

        if missing:
            parts.append(f"missing={format_hex_array(missing)}")

        if extra:
            parts.append(f"extra={format_hex_array(extra)}")

        parts.append(f"expected={format_hex_array(expected_hexes)}")
        parts.append(f"actual={format_hex_array(actual_hexes)}")

        errors.append("HEX MISMATCH | " + " | ".join(parts))

    return rel_path, errors, records


def build_imported_sdt(binary_data: bytes, records: list[tuple[str, str]]) -> bytes:
    offset = binary_data.find(b"\x00\x00\x00\x00\x18\x00\x00\x00")
    if offset == -1:
        raise ValueError("Hex sequence not found in binary file")

    offset_end = offset - 16
    if offset_end < 0:
        raise ValueError("Invalid header layout")

    offset_end_int_1 = struct.unpack("<I", binary_data[offset_end:offset_end + 4])[0]
    offset_end_int_2 = struct.unpack("<I", binary_data[offset_end + 4:offset_end + 8])[0]
    offset_end_int_3 = struct.unpack("<I", binary_data[offset_end + 8:offset_end + 12])[0]
    offset_end_int_4 = struct.unpack("<I", binary_data[offset_end + 12:offset_end + 16])[0]

    text_count = struct.unpack("<I", binary_data[offset + 8:offset + 12])[0]

    if text_count != len(records):
        raise ValueError(f"Text count mismatch: gcx_text_count={text_count} csv_text_count={len(records)}")

    binary_data_new = bytearray(binary_data[:offset_end])

    new_offset = (text_count * 4) + 4

    for key, value in records:
        if key == "0xffffffff":
            continue

        new_offset += len(value.encode("utf-8")) + 1

    new_offset_end_3 = (new_offset + offset + 8) - (offset - 16)

    data_offset = offset_end_int_1 - offset_end_int_2
    ps2_data_offset = offset_end_int_3 - offset_end_int_2
    ps2_data = offset_end_int_4 - offset_end_int_2

    binary_data_new += struct.pack("<I", new_offset_end_3 + data_offset)
    binary_data_new += struct.pack("<I", new_offset_end_3)
    binary_data_new += struct.pack("<I", new_offset_end_3 + ps2_data_offset)
    binary_data_new += struct.pack("<I", new_offset_end_3 + ps2_data)
    binary_data_new += binary_data[offset_end + 16:offset_end + 28]

    new_offset = (text_count * 4) + 4

    for key, value in records:
        if key == "0xffffffff":
            binary_data_new += struct.pack("<I", 0xFFFFFFFF)
        else:
            binary_data_new += struct.pack("<I", new_offset)
            new_offset += len(value.encode("utf-8")) + 1

    for key, value in records:
        if key != "0xffffffff":
            binary_data_new += value.encode("utf-8") + b"\x00"

    new_offset_end = offset_end_int_2 + (offset - 16)
    binary_data_new += binary_data[new_offset_end:]

    return bytes(binary_data_new)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("wb") as f:
        f.write(data)
    temp_path.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    temp_path.replace(path)


def csv_escape(value: str) -> str:
    if any(ch in value for ch in [",", '"', "\n"]):
        return '"' + value.replace('"', '""') + '"'
    return value


def read_existing_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists() or not path.is_file():
        return {}

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            return {}

        required_fields = {
            "output_sdt_path",
            "output_sdt_sha1",
            "original_sdt_sha1",
            "relative_sdt_path",
            "csv_sha1",
        }

        if not required_fields.issubset(set(reader.fieldnames)):
            return {}

        result: dict[str, dict[str, str]] = {}

        for row in reader:
            relative_sdt_path = (row.get("relative_sdt_path") or "").strip()
            if not relative_sdt_path:
                continue

            result[relative_sdt_path] = {
                "output_sdt_path": (row.get("output_sdt_path") or "").strip(),
                "output_sdt_sha1": (row.get("output_sdt_sha1") or "").strip().lower(),
                "original_sdt_sha1": (row.get("original_sdt_sha1") or "").strip().lower(),
                "relative_sdt_path": relative_sdt_path,
                "csv_sha1": (row.get("csv_sha1") or "").strip().lower(),
            }

        return result


def import_worker(
    row: dict[str, str],
    records: list[tuple[str, str]],
) -> tuple[str, dict[str, str] | None, str | None]:
    rel_csv_path = row["relative_csv_path"].strip()
    rel_sdt_path = row.get("relative_sdt_path", "").strip()

    if not rel_sdt_path:
        return rel_csv_path, None, "Missing relative_sdt_path"

    source_sdt_path = GAME_ROOT / Path(rel_sdt_path)
    if not source_sdt_path.exists() or not source_sdt_path.is_file():
        return rel_csv_path, None, f"Missing source SDT: {source_sdt_path}"

    output_sdt_path = OUTPUT_ROOT / Path(rel_sdt_path)

    try:
        original_sdt_sha1 = sha1_of_file(source_sdt_path)
        csv_sha1 = sha1_of_file(SCRIPT_DIR / Path(rel_csv_path))
        binary_data = source_sdt_path.read_bytes()
        rebuilt_data = build_imported_sdt(binary_data, records)
        atomic_write_bytes(output_sdt_path, rebuilt_data)
        output_sdt_sha1 = sha1_of_file(output_sdt_path)
    except Exception as exc:
        return rel_csv_path, None, str(exc)

    manifest_row = {
        "output_sdt_path": str(output_sdt_path),
        "output_sdt_sha1": output_sdt_sha1,
        "original_sdt_sha1": original_sdt_sha1,
        "relative_sdt_path": rel_sdt_path,
        "csv_sha1": csv_sha1,
        "built_unix_time": str(int(time.time())),
    }

    return rel_csv_path, manifest_row, None


def write_manifest(rows: list[dict[str, str]]) -> None:
    rows_sorted = sorted(rows, key=lambda row: row["relative_sdt_path"].lower())

    output_lines: list[str] = []
    output_lines.append(
        "output_sdt_path,output_sdt_sha1,original_sdt_sha1,relative_sdt_path,csv_sha1,built_unix_time"
    )

    for row in rows_sorted:
        output_lines.append(
            ",".join(
                [
                    csv_escape(row["output_sdt_path"]),
                    csv_escape(row["output_sdt_sha1"]),
                    csv_escape(row["original_sdt_sha1"]),
                    csv_escape(row["relative_sdt_path"]),
                    csv_escape(row["csv_sha1"]),
                    csv_escape(row.get("built_unix_time", "")),
                ]
            )
        )

    atomic_write_text(OUTPUT_MANIFEST, "\n".join(output_lines) + "\n")


def main() -> int:
    if not SHA1_CSV.exists():
        print(f"[ERROR] Missing required file: {SHA1_CSV}")
        wait_for_exit()
        return 1

    try:
        with SHA1_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                print(f"[ERROR] Invalid CSV header in: {SHA1_CSV}")
                wait_for_exit()
                return 1

            required_fields = {
                "relative_csv_path",
                "csv_sha1",
                "hex_values",
                "relative_sdt_path",
                "sdt_sha1",
            }
            missing_fields = required_fields - set(reader.fieldnames)

            if missing_fields:
                print(
                    "[ERROR] Missing required columns in _csv_sha1s.csv: "
                    + ", ".join(sorted(missing_fields))
                )
                wait_for_exit()
                return 1

            rows = [dict(row) for row in reader]
    except Exception as exc:
        print(f"[ERROR] Failed to read {SHA1_CSV}: {exc}")
        wait_for_exit()
        return 1

    row_by_rel_path: dict[str, dict[str, str]] = {}
    errors: list[tuple[str, str]] = []
    changed_rows: list[dict[str, str]] = []

    for row in rows:
        rel_path = row.get("relative_csv_path", "").strip()

        if not rel_path:
            errors.append(("<unknown>", "Missing relative_csv_path"))
            continue

        if rel_path in row_by_rel_path:
            errors.append((rel_path, "Duplicate relative_csv_path in _csv_sha1s.csv"))
            continue

        row_by_rel_path[rel_path] = row

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(hash_worker, row) for row in row_by_rel_path.values()]

        for future in as_completed(futures):
            rel_path, expected_sha1, actual_sha1, error = future.result()

            if error is not None:
                errors.append((rel_path or "<unknown>", error))
                continue

            if not expected_sha1:
                errors.append((rel_path, "Missing expected csv_sha1"))
                continue

            if actual_sha1 != expected_sha1:
                row = row_by_rel_path[rel_path]
                row["_actual_csv_sha1"] = actual_sha1
                changed_rows.append(row)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(verify_sdt_worker, row) for row in row_by_rel_path.values()]

        for future in as_completed(futures):
            rel_path, error = future.result()

            if error is not None:
                errors.append((rel_path, error))

    verify_errors: list[tuple[str, str]] = []
    changed_records: dict[str, list[tuple[str, str]]] = {}

    if changed_rows:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(verify_changed_file, row) for row in changed_rows]

            for future in as_completed(futures):
                rel_path, file_errors, records = future.result()

                for error in file_errors:
                    verify_errors.append((rel_path, error))

                if not file_errors and records is not None:
                    changed_records[rel_path] = records

    changed_rows.sort(key=lambda row: row["relative_csv_path"].strip().lower())
    errors.sort(key=lambda item: item[0].lower())
    verify_errors.sort(key=lambda item: (item[0].lower(), item[1].lower()))

    for row in changed_rows:
        rel_path = row["relative_csv_path"].strip()
        expected_sha1 = row.get("csv_sha1", "").strip().lower()
        actual_sha1 = row.get("_actual_csv_sha1", "").strip().lower()
        print(f"[CHANGED] {rel_path}: expected_sha1={expected_sha1} actual_sha1={actual_sha1}")

    if errors or verify_errors:
        print("")

        for rel_path, message in errors:
            print(f"[ERROR] {rel_path}: {message}")

        for rel_path, message in verify_errors:
            print(f"[ERROR] {rel_path}: {message}")

        wait_for_exit()
        return 1

    existing_manifest = read_existing_manifest(OUTPUT_MANIFEST)
    manifest_rows_by_rel_sdt = dict(existing_manifest)

    if not changed_rows:
        print("No changed CSVs found.")
        return 0

    rows_to_import: list[dict[str, str]] = []
    skipped_rows: list[tuple[str, str]] = []

    for row in changed_rows:
        rel_csv_path = row["relative_csv_path"].strip()
        rel_sdt_path = row.get("relative_sdt_path", "").strip()
        actual_csv_sha1 = row.get("_actual_csv_sha1", "").strip().lower()
        existing_entry = existing_manifest.get(rel_sdt_path)

        if existing_entry is None:
            rows_to_import.append(row)
            continue

        output_path_text = existing_entry.get("output_sdt_path", "").strip()
        output_path = Path(output_path_text) if output_path_text else OUTPUT_ROOT / Path(rel_sdt_path)
        output_exists = output_path.exists() and output_path.is_file()

        if existing_entry.get("csv_sha1", "").lower() != actual_csv_sha1:
            rows_to_import.append(row)
            continue

        if not output_exists:
            rows_to_import.append(row)
            continue

        skipped_rows.append((rel_csv_path, rel_sdt_path))

    import_errors: list[tuple[str, str]] = []
    built_rows: list[dict[str, str]] = []

    if rows_to_import:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(
                    import_worker,
                    row,
                    changed_records[row["relative_csv_path"].strip()],
                )
                for row in rows_to_import
            ]

            for future in as_completed(futures):
                rel_csv_path, manifest_row, error = future.result()

                if error is not None:
                    import_errors.append((rel_csv_path, error))
                    continue

                if manifest_row is not None:
                    built_rows.append(manifest_row)

    import_errors.sort(key=lambda item: item[0].lower())
    built_rows.sort(key=lambda row: row["relative_sdt_path"].lower())
    skipped_rows.sort(key=lambda item: item[0].lower())

    if import_errors:
        print("")

        for rel_path, message in import_errors:
            print(f"[ERROR] {rel_path}: Import failed: {message}")

        wait_for_exit()
        return 1

    for row in built_rows:
        manifest_rows_by_rel_sdt[row["relative_sdt_path"]] = row

    try:
        write_manifest(list(manifest_rows_by_rel_sdt.values()))
    except Exception as exc:
        print(f"[ERROR] Failed to write manifest: {exc}")
        wait_for_exit()
        return 1

    for row in built_rows:
        print(f"[BUILT] {row['relative_sdt_path']}")

    for rel_csv_path, rel_sdt_path in skipped_rows:
        print(f"[SKIPPED] {rel_csv_path} -> {rel_sdt_path}: manifest csv_sha1 already matches and output exists")

    print("")
    print(f"Built {len(built_rows)} SDT file(s).")
    print(f"Skipped {len(skipped_rows)} SDT file(s).")
    print(f"Manifest: {OUTPUT_MANIFEST}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
