from __future__ import annotations

import binascii
import csv
import hashlib
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


LOG_STARTING_FILE = True

SKIP_SDT_PATHS = {
    "gr/codec/_bp/cb_no_response.sdt",
    "sp/codec/_bp/cb_no_response.sdt",
    "jp/codec/_bp/cb_no_response.sdt",
    "fr/codec/_bp/cb_no_response.sdt",
    "it/codec/_bp/cb_no_response.sdt",
    "fr/codec/_bp/radiotest3.sdt",
    "fr/codec/_bp/test.sdt",
    "gr/codec/_bp/radiotest3.sdt",
    "gr/codec/_bp/test.sdt",
    "it/codec/_bp/radiotest3.sdt",
    "it/codec/_bp/test.sdt",
    "jp/codec/_bp/radiotest3.sdt",
    "jp/codec/_bp/test.sdt",
    "sp/codec/_bp/radiotest3.sdt",
    "sp/codec/_bp/test.sdt",
    "test.sdt",
    "radiotest3.sdt",
    "cb_no_response.sdt",
}

OUTPUT_ROOT = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Script CSVs\Radio Calls")
#OUTPUT_ROOT = Path(r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Script CSVs\Delta Radio Calls")
PATTERN = binascii.unhexlify("0000000018000000")
MAX_WORKERS = (os.cpu_count() * 2)
SKIP_DIR_NAMES = {"demo", "bgm", "bgm_2", "movie", "vox", "vox_2"}
SHA1_CSV_NAME = "_csv_sha1s.csv"
SHA1_BUFFER_SIZE = 8 * 1024 * 1024
PROGRESS_UPDATE_INTERVAL = 5.0
SHA1_FLUSH_INTERVAL_SECONDS = 15.0
SHA1_FORCE_FLUSH_FILE_COUNT = 150
SHA1_FORCE_FLUSH_MAX_AGE_SECONDS = 30.0

#SCRIPT_DIR = Path(r"J:\Mega\Games\MG Master Collection\Self made mods\delta codec calls")
SCRIPT_DIR = Path(r"G:\Steam\steamapps\common\MGS3")

_progress_lock = threading.Lock()
_last_progress_line = ""


def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(SHA1_BUFFER_SIZE), b""):
            h.update(chunk)

    return h.hexdigest()


def extract_texts_from_file(input_path: Path) -> list[tuple[int, str]]:
    with input_path.open("rb") as file:
        binary_data = file.read()

    data_pairs: list[tuple[int, str]] = []

    index = 0
    while index < len(binary_data):
        index = binary_data.find(PATTERN, index)
        if index == -1:
            break

        offset_length = int.from_bytes(
            binary_data[index + len(PATTERN):index + len(PATTERN) + 4],
            byteorder="little",
        )
        index += len(PATTERN) + 4

        text_offsets: list[int] = []
        for _ in range(offset_length):
            text_offset = int.from_bytes(
                binary_data[index:index + 4],
                byteorder="little",
            )
            text_offsets.append(text_offset)
            index += 4

        index -= (4 * offset_length) + 4

        for text_offset in text_offsets:
            text_start = index + text_offset
            text_end = binary_data.find(b"\x00", text_start)

            if text_end == -1:
                text_end = len(binary_data)

            text = binary_data[text_start:text_end].decode("utf-8", errors="ignore")
            data_pairs.append((text_offset, text))

    return data_pairs


def build_output_path(input_path: Path) -> Path:
    relative_path = input_path.relative_to(SCRIPT_DIR)
    return (OUTPUT_ROOT / relative_path).with_suffix(".csv")


def discover_sdt_files(root: Path) -> list[Path]:
    results: list[Path] = []

    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = sorted(
            [
                dir_name
                for dir_name in dir_names
                if dir_name.lower() not in SKIP_DIR_NAMES
            ],
            key=str.lower,
        )

        current_root_path = Path(current_root)

        for file_name in sorted(file_names, key=str.lower):
            if not file_name.lower().endswith(".sdt"):
                continue

            full_path = current_root_path / file_name
            rel_path = full_path.relative_to(root).as_posix().lower()

            if rel_path in SKIP_SDT_PATHS:
                continue

            results.append(full_path)

    return results


def is_csv_empty(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False

    if path.stat().st_size == 0:
        return True

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if any(cell.strip() for cell in row):
                    return False
    except Exception:
        return False

    return True


def relative_output_csv_path(csv_path: Path) -> str:
    return csv_path.relative_to(OUTPUT_ROOT).as_posix()


def relative_input_sdt_path(sdt_path: Path) -> str:
    return sdt_path.relative_to(SCRIPT_DIR).as_posix()


def load_existing_sha1_manifest(manifest_path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}

    if not manifest_path.exists():
        return rows

    try:
        with manifest_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                relative_csv_path = (row.get("relative_csv_path") or "").strip()
                if not relative_csv_path:
                    continue

                rows[relative_csv_path] = {
                    "relative_csv_path": relative_csv_path,
                    "csv_sha1": (row.get("csv_sha1") or "").strip(),
                    "relative_sdt_path": (row.get("relative_sdt_path") or "").strip(),
                    "sdt_sha1": (row.get("sdt_sha1") or "").strip(),
                }
    except Exception as exc:
        print_progress_safe(f"[ERROR] Failed to read SHA1 CSV {manifest_path}: {exc}")

    return rows


def write_sha1_manifest(
    manifest_path: Path,
    manifest_rows: dict[str, dict[str, str]],
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_keys = sorted(manifest_rows.keys(), key=str.lower)

    fd, temp_path_str = tempfile.mkstemp(
        prefix=manifest_path.stem + "_",
        suffix=".tmp",
        dir=str(manifest_path.parent),
    )
    os.close(fd)
    temp_path = Path(temp_path_str)

    try:
        with temp_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(["relative_csv_path", "csv_sha1", "relative_sdt_path", "sdt_sha1"])

            for key in sorted_keys:
                row = manifest_rows[key]
                writer.writerow(
                    [
                        row["relative_csv_path"],
                        row["csv_sha1"],
                        row["relative_sdt_path"],
                        row["sdt_sha1"],
                    ]
                )

        os.replace(temp_path, manifest_path)
    except Exception:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass
        raise


def prune_missing_csv_manifest_rows(
    manifest_rows: dict[str, dict[str, str]],
) -> int:
    removed_count = 0
    keys_to_remove: list[str] = []

    for rel_csv_path in manifest_rows.keys():
        csv_path = OUTPUT_ROOT / rel_csv_path
        if not csv_path.is_file():
            keys_to_remove.append(rel_csv_path)

    for key in keys_to_remove:
        del manifest_rows[key]
        removed_count += 1

    return removed_count


def remove_empty_csvs(root: Path) -> int:
    if not root.exists():
        return 0

    removed_count = 0

    for csv_path in sorted(root.rglob("*.csv")):
        if csv_path.name == SHA1_CSV_NAME:
            continue

        if not is_csv_empty(csv_path):
            continue

        try:
            csv_path.unlink()
            removed_count += 1
            print_progress_safe(f"[DELETE EMPTY CSV] {csv_path}")
        except Exception as exc:
            print_progress_safe(f"[ERROR] Failed to delete empty CSV {csv_path}: {exc}")

    return removed_count


def remove_untracked_csvs(root: Path, manifest_rows: dict[str, dict[str, str]]) -> int:
    if not root.exists():
        return 0

    valid_relative_paths = set(manifest_rows.keys())
    removed_count = 0

    for csv_path in sorted(root.rglob("*.csv")):
        if csv_path.name == SHA1_CSV_NAME:
            continue

        rel_path = relative_output_csv_path(csv_path)
        if rel_path in valid_relative_paths:
            continue

        try:
            csv_path.unlink()
            removed_count += 1
            print_progress_safe(f"[DELETE UNTRACKED CSV] {csv_path}")
        except Exception as exc:
            print_progress_safe(f"[ERROR] Failed to delete untracked CSV {csv_path}: {exc}")

    return removed_count


def remove_empty_folders(root: Path) -> int:
    if not root.exists():
        return 0

    removed_count = 0

    all_dirs = sorted(
        [path for path in root.rglob("*") if path.is_dir()],
        key=lambda path: len(path.parts),
        reverse=True,
    )

    for folder in all_dirs:
        try:
            next(folder.iterdir())
        except StopIteration:
            try:
                folder.rmdir()
                removed_count += 1
                print_progress_safe(f"[DELETE EMPTY FOLDER] {folder}")
            except Exception as exc:
                print_progress_safe(f"[ERROR] Failed to delete empty folder {folder}: {exc}")
        except Exception as exc:
            print_progress_safe(f"[ERROR] Failed to inspect folder {folder}: {exc}")

    return removed_count


def export_file(input_path: Path) -> tuple[bool, Path, str, str | None, str | None]:
    try:
        if LOG_STARTING_FILE:
            print_progress_safe(f"[START] {input_path}")

        output_path = build_output_path(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        sdt_sha1 = sha1_of_file(input_path)
        data_pairs = extract_texts_from_file(input_path)

        if not data_pairs:
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            return True, input_path, "[EMPTY]", None, sdt_sha1

        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file, lineterminator="\n")
            for offset, text in data_pairs:
                csv_writer.writerow([hex(offset), text, text])

        if is_csv_empty(output_path):
            try:
                output_path.unlink()
                return True, input_path, "[EMPTY]", None, sdt_sha1
            except Exception as exc:
                return False, input_path, f"Failed to delete empty CSV {output_path}: {exc}", None, sdt_sha1

        csv_sha1 = sha1_of_file(output_path)
        return True, input_path, str(output_path), csv_sha1, sdt_sha1
    except Exception as exc:
        return False, input_path, str(exc), None, None


def format_eta(seconds: float) -> str:
    if seconds < 0:
        seconds = 0

    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def build_progress_line(
    total_files: int,
    completed: int,
    success_count: int,
    error_count: int,
    skipped_count: int,
    start_time: float,
) -> str:
    elapsed = time.time() - start_time
    percent = (completed / total_files * 100.0) if total_files else 100.0

    if completed > 0 and elapsed > 0:
        rate = completed / elapsed
        remaining = total_files - completed
        eta_seconds = remaining / rate if rate > 0 else 0.0
    else:
        eta_seconds = 0.0

    return (
        f"[PROGRESS] {completed}/{total_files} "
        f"({percent:6.2f}%) | OK: {success_count} | Skipped: {skipped_count} | Errors: {error_count} | "
        f"Elapsed: {format_eta(elapsed)} | ETA: {format_eta(eta_seconds)}"
    )


def clear_progress_line() -> None:
    global _last_progress_line

    with _progress_lock:
        if _last_progress_line:
            sys.stdout.write("\r" + (" " * len(_last_progress_line)) + "\r")
            sys.stdout.flush()
            _last_progress_line = ""


def render_progress_line(line: str) -> None:
    global _last_progress_line

    with _progress_lock:
        padded_line = line
        if len(_last_progress_line) > len(padded_line):
            padded_line = padded_line + (" " * (len(_last_progress_line) - len(padded_line)))

        sys.stdout.write("\r" + padded_line)
        sys.stdout.flush()
        _last_progress_line = padded_line


def print_progress_safe(message: str) -> None:
    with _progress_lock:
        current_line = _last_progress_line

        if current_line:
            sys.stdout.write("\r" + (" " * len(current_line)) + "\r")
        sys.stdout.write(message + "\n")
        if current_line:
            sys.stdout.write(current_line)
        sys.stdout.flush()


def progress_worker(
    total_files: int,
    counters: dict[str, int],
    counters_lock: threading.Lock,
    stop_event: threading.Event,
    start_time: float,
) -> None:
    while not stop_event.wait(PROGRESS_UPDATE_INTERVAL):
        with counters_lock:
            completed = counters["completed"]
            success_count = counters["success"]
            error_count = counters["error"]
            skipped_count = counters["skipped"]

        line = build_progress_line(
            total_files=total_files,
            completed=completed,
            success_count=success_count,
            error_count=error_count,
            skipped_count=skipped_count,
            start_time=start_time,
        )
        render_progress_line(line)


def should_flush_manifest(
    *,
    pending_completed_since_flush: int,
    last_flush_time: float,
    now: float,
) -> bool:
    if pending_completed_since_flush <= 0:
        return False

    if now - last_flush_time >= SHA1_FLUSH_INTERVAL_SECONDS:
        return True

    if pending_completed_since_flush >= SHA1_FORCE_FLUSH_FILE_COUNT and (now - last_flush_time) < SHA1_FORCE_FLUSH_MAX_AGE_SECONDS:
        return True

    return False


def flush_manifest_if_needed(
    *,
    manifest_path: Path,
    manifest_rows: dict[str, dict[str, str]],
    manifest_lock: threading.Lock,
    pending_completed_since_flush_ref: dict[str, int],
    last_flush_time_ref: dict[str, float],
    force: bool = False,
) -> bool:
    now = time.time()

    with manifest_lock:
        pending = pending_completed_since_flush_ref["value"]
        last_flush_time = last_flush_time_ref["value"]

        if not force and not should_flush_manifest(
            pending_completed_since_flush=pending,
            last_flush_time=last_flush_time,
            now=now,
        ):
            return False

        try:
            write_sha1_manifest(manifest_path, manifest_rows)
            pending_completed_since_flush_ref["value"] = 0
            last_flush_time_ref["value"] = now
            return True
        except Exception as exc:
            print_progress_safe(f"[ERROR] Failed to write SHA1 CSV {manifest_path}: {exc}")
            return False


def main() -> None:
    print("MGS3 *.sdt Export (Originally by Giza, modified by Afevis for CBFC)")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    manifest_path = OUTPUT_ROOT / SHA1_CSV_NAME
    manifest_rows = load_existing_sha1_manifest(manifest_path)
    manifest_lock = threading.Lock()

    removed_missing_manifest_rows_pre = prune_missing_csv_manifest_rows(manifest_rows)
    if removed_missing_manifest_rows_pre:
        write_sha1_manifest(manifest_path, manifest_rows)
        print_progress_safe(f"[INFO] Missing manifest CSV rows removed before scan: {removed_missing_manifest_rows_pre}")

    removed_empty_csvs_pre = remove_empty_csvs(OUTPUT_ROOT)
    removed_untracked_csvs_pre = remove_untracked_csvs(OUTPUT_ROOT, manifest_rows)
    removed_empty_folders_pre = remove_empty_folders(OUTPUT_ROOT)

    removed_missing_manifest_rows_post_cleanup = prune_missing_csv_manifest_rows(manifest_rows)
    if removed_missing_manifest_rows_post_cleanup:
        write_sha1_manifest(manifest_path, manifest_rows)
        print_progress_safe(f"[INFO] Missing manifest CSV rows removed after cleanup: {removed_missing_manifest_rows_post_cleanup}")

    if removed_empty_csvs_pre:
        print_progress_safe(f"[INFO] Empty CSVs removed before scan: {removed_empty_csvs_pre}")
    if removed_untracked_csvs_pre:
        print_progress_safe(f"[INFO] Untracked CSVs removed before scan: {removed_untracked_csvs_pre}")
    if removed_empty_folders_pre:
        print_progress_safe(f"[INFO] Empty folders removed before scan: {removed_empty_folders_pre}")

    tracked_relative_sdt_paths = {
        row["relative_sdt_path"]
        for row in manifest_rows.values()
        if row["relative_sdt_path"]
    }

    all_sdt_files = discover_sdt_files(SCRIPT_DIR)

    if not all_sdt_files:
        print(f"[INFO] No .sdt files found under: {SCRIPT_DIR}")
        with manifest_lock:
            write_sha1_manifest(manifest_path, manifest_rows)
        print(f"[INFO] SHA1 CSV written: {manifest_path}")
        return

    sdt_files_to_process: list[Path] = []
    skipped_existing_count = 0

    for sdt_path in all_sdt_files:
        rel_sdt_path = relative_input_sdt_path(sdt_path)
        if rel_sdt_path in tracked_relative_sdt_paths:
            skipped_existing_count += 1
            continue

        sdt_files_to_process.append(sdt_path)

    print(f"[INFO] Found {len(all_sdt_files)} .sdt files")
    print(f"[INFO] Already tracked in SHA1 CSV: {skipped_existing_count}")
    print(f"[INFO] Remaining to process: {len(sdt_files_to_process)}")
    print(f"[INFO] Using {MAX_WORKERS} worker threads")

    total_for_progress = len(all_sdt_files)

    counters = {
        "completed": skipped_existing_count,
        "success": 0,
        "error": 0,
        "skipped": skipped_existing_count,
    }
    counters_lock = threading.Lock()

    start_time = time.time()
    stop_event = threading.Event()
    pending_completed_since_flush_ref = {"value": 0}
    last_flush_time_ref = {"value": time.time()}

    initial_line = build_progress_line(
        total_files=total_for_progress,
        completed=counters["completed"],
        success_count=counters["success"],
        error_count=counters["error"],
        skipped_count=counters["skipped"],
        start_time=start_time,
    )
    render_progress_line(initial_line)

    progress_thread = threading.Thread(
        target=progress_worker,
        args=(total_for_progress, counters, counters_lock, stop_event, start_time),
        daemon=True,
    )
    progress_thread.start()

    if sdt_files_to_process:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(export_file, input_path) for input_path in sdt_files_to_process]

            for future in as_completed(futures):
                try:
                    ok, input_path, message, csv_sha1, sdt_sha1 = future.result()
                except Exception as exc:
                    ok = False
                    input_path = Path("[unknown]")
                    message = str(exc)
                    csv_sha1 = None
                    sdt_sha1 = None

                with counters_lock:
                    counters["completed"] += 1
                    if ok:
                        counters["success"] += 1
                    else:
                        counters["error"] += 1

                    completed = counters["completed"]
                    success_count = counters["success"]
                    error_count = counters["error"]
                    skipped_count = counters["skipped"]

                if ok:
                    if csv_sha1 is not None and sdt_sha1 is not None:
                        output_path = build_output_path(input_path)
                        rel_csv_path = relative_output_csv_path(output_path)
                        rel_sdt_path = relative_input_sdt_path(input_path)

                        with manifest_lock:
                            manifest_rows[rel_csv_path] = {
                                "relative_csv_path": rel_csv_path,
                                "csv_sha1": csv_sha1,
                                "relative_sdt_path": rel_sdt_path,
                                "sdt_sha1": sdt_sha1,
                            }
                            pending_completed_since_flush_ref["value"] += 1

                        flush_manifest_if_needed(
                            manifest_path=manifest_path,
                            manifest_rows=manifest_rows,
                            manifest_lock=manifest_lock,
                            pending_completed_since_flush_ref=pending_completed_since_flush_ref,
                            last_flush_time_ref=last_flush_time_ref,
                        )
                else:
                    print_progress_safe(f"[ERROR] {input_path}: {message}")

                line = build_progress_line(
                    total_files=total_for_progress,
                    completed=completed,
                    success_count=success_count,
                    error_count=error_count,
                    skipped_count=skipped_count,
                    start_time=start_time,
                )
                render_progress_line(line)

    stop_event.set()
    progress_thread.join()

    flush_manifest_if_needed(
        manifest_path=manifest_path,
        manifest_rows=manifest_rows,
        manifest_lock=manifest_lock,
        pending_completed_since_flush_ref=pending_completed_since_flush_ref,
        last_flush_time_ref=last_flush_time_ref,
        force=True,
    )

    removed_empty_csvs_post = remove_empty_csvs(OUTPUT_ROOT)
    removed_untracked_csvs_post = remove_untracked_csvs(OUTPUT_ROOT, manifest_rows)
    removed_empty_folders_post = remove_empty_folders(OUTPUT_ROOT)

    removed_missing_manifest_rows_post = prune_missing_csv_manifest_rows(manifest_rows)

    with manifest_lock:
        write_sha1_manifest(manifest_path, manifest_rows)

    with counters_lock:
        final_completed = counters["completed"]
        final_success = counters["success"]
        final_error = counters["error"]
        final_skipped = counters["skipped"]

    final_line = build_progress_line(
        total_files=total_for_progress,
        completed=final_completed,
        success_count=final_success,
        error_count=final_error,
        skipped_count=final_skipped,
        start_time=start_time,
    )
    render_progress_line(final_line)
    sys.stdout.write("\n")
    sys.stdout.flush()

    print(f"[DONE] Exported: {final_success}, Skipped: {final_skipped}, Errors: {final_error}")
    print(f"[INFO] Missing manifest CSV rows removed before scan: {removed_missing_manifest_rows_pre}")
    print(f"[INFO] Missing manifest CSV rows removed after cleanup: {removed_missing_manifest_rows_post_cleanup}")
    print(f"[INFO] Empty CSVs removed before scan: {removed_empty_csvs_pre}")
    print(f"[INFO] Untracked CSVs removed before scan: {removed_untracked_csvs_pre}")
    print(f"[INFO] Empty folders removed before scan: {removed_empty_folders_pre}")
    print(f"[INFO] Empty CSVs removed after run: {removed_empty_csvs_post}")
    print(f"[INFO] Untracked CSVs removed after run: {removed_untracked_csvs_post}")
    print(f"[INFO] Empty folders removed after run: {removed_empty_folders_post}")
    print(f"[INFO] Missing manifest CSV rows removed after run: {removed_missing_manifest_rows_post}")
    print(f"[INFO] SHA1 CSV written: {manifest_path}")


if __name__ == "__main__":
    main()