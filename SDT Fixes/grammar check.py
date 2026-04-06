from __future__ import annotations

import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import local
from typing import Any


ROOT_DIR = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\original_subtitles")
OUTPUT_CSV = ROOT_DIR / "_eng_grammar_results.csv"

MAX_WORKERS = max(4, os.cpu_count() or 4)

_thread_local = local()


def get_language_tool():
    try:
        import language_tool_python
    except ImportError:
        print("Missing dependency: language-tool-python")
        print("Install it with: pip install language-tool-python")
        sys.exit(1)

    tool = getattr(_thread_local, "tool", None)

    if tool is None:
        _thread_local.tool = language_tool_python.LanguageTool("en-US")
        tool = _thread_local.tool

    return tool


def get_csv_files(root_dir: Path) -> list[Path]:
    return sorted(
        path for path in root_dir.rglob("*.csv")
        if path.name.lower() != OUTPUT_CSV.name.lower()
    )


def safe_get(row: dict[str, Any], key: str) -> str:
    value = row.get(key, "")

    if value is None:
        return ""

    return str(value)


def format_replacements(replacements: list[str]) -> str:
    if not replacements:
        return ""

    return " | ".join(replacements[:10])


def process_csv(path: Path, root_dir: Path) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    tool = get_language_tool()

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                return results

            row_number = 1

            for row in reader:
                row_number += 1

                lang_id = safe_get(row, "Lang ID").strip()

                if lang_id != "[ENG]":
                    continue

                text = safe_get(row, "Text").strip()

                if not text:
                    continue

                matches = tool.check(text)

                for match in matches:
                    context = match.context
                    context_offset = match.offsetInContext
                    context_length = match.errorLength

                    issue_text = ""
                    if (
                        context is not None
                        and context_offset is not None
                        and context_length is not None
                        and context_offset >= 0
                        and context_length > 0
                        and context_offset + context_length <= len(context)
                    ):
                        issue_text = context[context_offset:context_offset + context_length]

                    results.append(
                        {
                            "relative_csv_path": path.relative_to(root_dir).as_posix(),
                            "row_number": str(row_number),
                            "start_time": safe_get(row, "Start Time").strip(),
                            "end_time": safe_get(row, "End Time").strip(),
                            "text": text,
                            "rule_id": getattr(match, "ruleId", "") or "",
                            "category": getattr(match, "category", "") or "",
                            "message": getattr(match, "message", "") or "",
                            "issue_text": issue_text,
                            "suggestions": format_replacements(getattr(match, "replacements", []) or []),
                            "offset": str(getattr(match, "offset", "") or ""),
                            "error_length": str(getattr(match, "errorLength", "") or ""),
                            "context": context or "",
                        }
                    )

    except Exception as e:
        results.append(
            {
                "relative_csv_path": path.relative_to(root_dir).as_posix(),
                "row_number": "",
                "start_time": "",
                "end_time": "",
                "text": "",
                "rule_id": "",
                "category": "ERROR",
                "message": str(e),
                "issue_text": "",
                "suggestions": "",
                "offset": "",
                "error_length": "",
                "context": "",
            }
        )

    return results


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "relative_csv_path",
        "row_number",
        "start_time",
        "end_time",
        "text",
        "rule_id",
        "category",
        "message",
        "issue_text",
        "suggestions",
        "offset",
        "error_length",
        "context",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def shutdown_thread_tools() -> None:
    tool = getattr(_thread_local, "tool", None)

    if tool is not None:
        try:
            tool.close()
        except Exception:
            pass


def main() -> None:
    if not ROOT_DIR.is_dir():
        print(f"Root directory does not exist: {ROOT_DIR}")
        sys.exit(1)

    csv_files = get_csv_files(ROOT_DIR)

    if not csv_files:
        print("No CSV files found.")
        sys.exit(0)

    all_results: list[dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_csv, path, ROOT_DIR): path
            for path in csv_files
        }

        completed = 0
        total = len(futures)

        for future in as_completed(futures):
            path = futures[future]
            completed += 1

            try:
                rows = future.result()
                all_results.extend(rows)
            except Exception as e:
                all_results.append(
                    {
                        "relative_csv_path": path.relative_to(ROOT_DIR).as_posix(),
                        "row_number": "",
                        "start_time": "",
                        "end_time": "",
                        "text": "",
                        "rule_id": "",
                        "category": "ERROR",
                        "message": str(e),
                        "issue_text": "",
                        "suggestions": "",
                        "offset": "",
                        "error_length": "",
                        "context": "",
                    }
                )

            print(f"[{completed}/{total}] {path.relative_to(ROOT_DIR).as_posix()}")

    all_results.sort(
        key=lambda row: (
            row["relative_csv_path"].lower(),
            int(row["row_number"]) if row["row_number"].isdigit() else 0,
            row["offset"].isdigit() and int(row["offset"]) or 0,
            row["rule_id"].lower(),
        )
    )

    write_results(OUTPUT_CSV, all_results)

    print()
    print(f"Scanned CSV files: {len(csv_files)}")
    print(f"Grammar issues found: {len(all_results)}")
    print(f"Output: {OUTPUT_CSV}")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutdown_thread_tools()