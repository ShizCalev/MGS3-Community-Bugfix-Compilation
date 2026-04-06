from __future__ import annotations

import csv
import hashlib
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SHA1_CSV = SCRIPT_DIR / "_csv_sha1s.csv"

MAX_WORKERS = max(4, os.cpu_count() or 4)
SHA1_BUFFER_SIZE = 8 * 1024 * 1024

LINE_PREFIX_HEX_RE = re.compile(r"^(0x[0-9A-Fa-f]+),")
HEX_VALUE_RE = re.compile(r"^0x[0-9a-f]+$")


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

        if HEX_VALUE_RE.fullmatch(hex_value) is None:
            raise ValueError(f"Invalid hex value: {hex_value!r}")

        result.add(hex_value)

    return result


def format_hex_array(values: set[str]) -> str:
    if not values:
        return "[]"

    ordered = sorted(values, key=lambda value: int(value, 16))
    return "[" + ",".join(ordered) + "]"


def scan_hexes_from_csv(path: Path) -> set[str]:
    matches: set[str] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for raw_line in f:
            line = raw_line.rstrip("\r\n")
            match = LINE_PREFIX_HEX_RE.match(line)

            if match is None:
                continue

            matches.add(match.group(1).lower())

    return matches


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


def verify_changed_file(row: dict[str, str]) -> tuple[str, str | None]:
    rel_path = row["relative_csv_path"].strip()
    csv_path = SCRIPT_DIR / Path(rel_path)

    try:
        expected_hexes = parse_hex_array(row.get("hex_values", "[]"))
    except Exception as exc:
        return rel_path, f"Invalid hex_values: {exc}"

    try:
        actual_hexes = scan_hexes_from_csv(csv_path)
    except Exception as exc:
        return rel_path, f"Hex scan error: {exc}"

    missing = expected_hexes - actual_hexes
    extra = actual_hexes - expected_hexes

    if not missing and not extra:
        return rel_path, None

    parts: list[str] = []

    if missing:
        parts.append(f"missing={format_hex_array(missing)}")

    if extra:
        parts.append(f"extra={format_hex_array(extra)}")

    parts.append(f"expected={format_hex_array(expected_hexes)}")
    parts.append(f"actual={format_hex_array(actual_hexes)}")

    return rel_path, " | ".join(parts)


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

            required_fields = {"relative_csv_path", "csv_sha1", "hex_values"}
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

    verify_errors: list[tuple[str, str]] = []

    if changed_rows:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(verify_changed_file, row) for row in changed_rows]

            for future in as_completed(futures):
                rel_path, error = future.result()

                if error is not None:
                    verify_errors.append((rel_path, error))

    changed_rows.sort(key=lambda row: row["relative_csv_path"].strip().lower())
    errors.sort(key=lambda item: item[0].lower())
    verify_errors.sort(key=lambda item: item[0].lower())

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
            print(f"[ERROR] {rel_path}: HEX MISMATCH | {message}")

        wait_for_exit()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())