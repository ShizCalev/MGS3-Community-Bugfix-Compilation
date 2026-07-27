from __future__ import annotations

import csv
import hashlib
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


# ==========================================================
# CONFIG
# ==========================================================
SEVENZIP_EXE = Path(r"C:\Program Files\7-Zip\7z.exe")

SCRIPT_DIR = Path(__file__).resolve().parent

HASH_MAX_WORKERS = 24
SHA1_BUFFER_SIZE = 4 * 1024 * 1024

PROGRESS_EVERY_FILES = 50
PROGRESS_EVERY_SECONDS = 1.5


# ==========================================================
# DATA
# ==========================================================
@dataclass(frozen=True)
class ArchiveEntry:
    path: str
    size: int


# ==========================================================
# HELPERS
# ==========================================================
def normalize_archive_path(path: str) -> str:
    path = path.replace("\\", "/").strip()

    while "//" in path:
        path = path.replace("//", "/")

    if path.startswith("./"):
        path = path[2:]

    return path


def is_archive_entry_file(path: Path) -> bool:
    name = path.name.lower()

    # Normal single-file ZIP archives.
    if name.endswith(".zip"):
        return True

    # Split ZIP archives: archive.zip.001, archive.zip.002, etc.
    # Only open the first volume; 7-Zip automatically reads the remaining parts.
    zip_volume_match = re.fullmatch(r".+\.zip\.(\d+)", name)
    if zip_volume_match:
        return int(zip_volume_match.group(1)) == 1

    # Old-style multipart RAR: archive.rar + archive.r00 + archive.r01.
    if name.endswith(".rar"):
        # New-style multipart RAR: archive.part01.rar, archive.part02.rar, etc.
        # Only open the first volume.
        rar_part_match = re.fullmatch(r".+\.part(\d+)\.rar", name)
        return rar_part_match is None or int(rar_part_match.group(1)) == 1

    return False


def find_archive_files_in_script_folder() -> list[Path]:
    return sorted(
        path
        for path in SCRIPT_DIR.iterdir()
        if path.is_file() and is_archive_entry_file(path)
    )


def parse_7z_paths(archive_path: Path) -> list[ArchiveEntry]:
    cmd = [
        str(SEVENZIP_EXE),
        "l",
        "-slt",
        str(archive_path),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )

    entries: list[ArchiveEntry] = []

    current_path: str | None = None
    current_size: int | None = None
    current_is_dir = False
    inside_file_entries = False

    def flush() -> None:
        nonlocal current_path
        nonlocal current_size
        nonlocal current_is_dir

        if current_path is not None and not current_is_dir:
            normalized = normalize_archive_path(current_path)

            if normalized:
                entries.append(
                    ArchiveEntry(
                        path=normalized,
                        size=current_size if current_size is not None else 0,
                    )
                )

        current_path = None
        current_size = None
        current_is_dir = False

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()

        # Everything before this separator describes the archive itself,
        # including a misleading "Path = ..." field. It is not a file entry.
        if not inside_file_entries:
            if line == "----------":
                inside_file_entries = True
            continue

        if not line:
            continue

        if line.startswith("Path = "):
            flush()
            current_path = line[len("Path = "):]
            continue

        if current_path is None:
            continue

        if line.startswith("Folder = "):
            current_is_dir = (line[len("Folder = "):].strip() == "+")
            continue

        if line.startswith("Size = "):
            value = line[len("Size = "):].strip()

            try:
                current_size = int(value)
            except ValueError:
                current_size = 0

            continue

    flush()
    return entries


def compute_entry_sha1(archive_path: Path, entry_path: str, expected_size: int) -> str:
    cmd = [
        str(SEVENZIP_EXE),
        "x",
        "-so",
        str(archive_path),
        entry_path,
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    sha1 = hashlib.sha1()
    bytes_hashed = 0

    assert process.stdout is not None

    while True:
        chunk = process.stdout.read(SHA1_BUFFER_SIZE)
        if not chunk:
            break
        sha1.update(chunk)
        bytes_hashed += len(chunk)

    stderr_data = b""
    if process.stderr is not None:
        stderr_data = process.stderr.read()

    return_code = process.wait()

    stderr_text = stderr_data.decode("utf-8", errors="replace").strip()

    if return_code != 0:
        raise RuntimeError(
            f"7z failed while hashing '{entry_path}'. Exit code: {return_code}. stderr: {stderr_text}"
        )

    if bytes_hashed != expected_size:
        raise RuntimeError(
            f"7z returned {bytes_hashed} bytes for '{entry_path}', but the archive listing says "
            f"{expected_size} bytes. stderr: {stderr_text}"
        )

    return sha1.hexdigest().lower()


def archive_output_stem(archive_path: Path) -> str:
    name = archive_path.name

    name = re.sub(r"\.zip\.0*1$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\.part0*1\.rar$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\.(zip|rar)$", "", name, flags=re.IGNORECASE)

    return name


def split_path_components(full_path: str) -> tuple[str, str, str, str]:
    p = Path(full_path)

    filename = p.name
    stem = p.stem
    ext = p.suffix[1:] if p.suffix.startswith(".") else p.suffix

    parent = str(p.parent).replace("\\", "/")
    if parent == ".":
        parent = ""

    return parent, filename, stem, ext


def format_bytes(num_bytes: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)

    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024.0

    return f"{num_bytes} B"


def format_duration(seconds: float) -> str:
    if seconds < 0:
        seconds = 0

    total_seconds = int(seconds + 0.5)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def compute_eta(seconds_elapsed: float, bytes_done: int, bytes_total: int) -> tuple[float, float]:
    if seconds_elapsed <= 0 or bytes_done <= 0 or bytes_total <= 0:
        return 0.0, 0.0

    bytes_per_second = bytes_done / seconds_elapsed
    remaining_bytes = max(0, bytes_total - bytes_done)

    if bytes_per_second <= 0:
        return bytes_per_second, 0.0

    eta_seconds = remaining_bytes / bytes_per_second
    return bytes_per_second, eta_seconds


def print_status_line(message: str) -> None:
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 160

    if len(message) >= terminal_width:
        message = message[: max(1, terminal_width - 1)]

    padded = message.ljust(max(1, terminal_width - 1))
    print(f"\r{padded}", end="", flush=True)


# ==========================================================
# MAIN WORK
# ==========================================================
def process_archive(
    archive_path: Path,
    entries: list[ArchiveEntry],
    global_bytes_done_before_archive: int,
    global_bytes_total_all_archives: int,
    global_start_time: float,
) -> int:
    if not archive_path.is_file():
        print(f"[!] Skipping missing archive: {archive_path}")
        return 0

    print(f"\n=== Processing: {archive_path.name} ===")

    archive_total_files = len(entries)
    archive_total_bytes = sum(entry.size for entry in entries)

    print(f"Found {archive_total_files} files")
    print(f"Archive size to hash: {format_bytes(archive_total_bytes)}")
    print(f"Workers: {HASH_MAX_WORKERS}")

    results: list[tuple[str, str, str, str, str, int, str] | None] = [None] * archive_total_files

    archive_start_time = time.perf_counter()
    archive_completed_files = 0
    archive_completed_bytes = 0
    last_progress_time = archive_start_time

    def worker(index: int, entry: ArchiveEntry) -> tuple[int, tuple[str, str, str, str, str, int, str], int]:
        sha1 = compute_entry_sha1(archive_path, entry.path, entry.size)
        rel_dir, filename, stem, ext = split_path_components(entry.path)

        row = (
            entry.path,
            rel_dir,
            filename,
            stem,
            ext,
            entry.size,
            sha1,
        )

        return index, row, entry.size

    with ThreadPoolExecutor(max_workers=HASH_MAX_WORKERS) as executor:
        futures = {
            executor.submit(worker, i, entry): i
            for i, entry in enumerate(entries)
        }

        for future in as_completed(futures):
            idx = futures[future]

            try:
                result_index, row, entry_size = future.result()
            except Exception as exc:
                raise RuntimeError(f"Failed processing entry {entries[idx].path}: {exc}") from exc

            results[result_index] = row
            archive_completed_files += 1
            archive_completed_bytes += entry_size

            now = time.perf_counter()
            should_print = False

            if archive_completed_files % PROGRESS_EVERY_FILES == 0:
                should_print = True

            if (now - last_progress_time) >= PROGRESS_EVERY_SECONDS:
                should_print = True

            if archive_completed_files == archive_total_files:
                should_print = True

            if should_print:
                archive_elapsed = now - archive_start_time
                total_elapsed = now - global_start_time

                archive_speed, archive_eta = compute_eta(archive_elapsed, archive_completed_bytes, archive_total_bytes)

                global_bytes_done = global_bytes_done_before_archive + archive_completed_bytes
                global_speed, global_eta = compute_eta(total_elapsed, global_bytes_done, global_bytes_total_all_archives)

                archive_percent = (archive_completed_bytes / archive_total_bytes * 100.0) if archive_total_bytes > 0 else 100.0
                global_percent = (global_bytes_done / global_bytes_total_all_archives * 100.0) if global_bytes_total_all_archives > 0 else 100.0

                status = (
                    f"[{archive_path.name}] "
                    f"{archive_completed_files}/{archive_total_files} files | "
                    f"{format_bytes(archive_completed_bytes)}/{format_bytes(archive_total_bytes)} ({archive_percent:.1f}%) | "
                    f"Archive speed {format_bytes(archive_speed)}/s | "
                    f"Archive ETA {format_duration(archive_eta)} | "
                    f"TOTAL {format_bytes(global_bytes_done)}/{format_bytes(global_bytes_total_all_archives)} ({global_percent:.1f}%) | "
                    f"TOTAL speed {format_bytes(global_speed)}/s | "
                    f"TOTAL ETA {format_duration(global_eta)}"
                )

                print_status_line(status)
                last_progress_time = now

    print()

    output_csv = SCRIPT_DIR / f"{archive_output_stem(archive_path)}.csv"

    print(f"Writing CSV: {output_csv.name}")

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "full_path",
            "relative_path_to_file",
            "filename_with_extension",
            "file_stem",
            "extension",
            "filesize",
            "sha1",
        ])

        for row in results:
            if row is not None:
                writer.writerow(row)

    archive_elapsed = time.perf_counter() - archive_start_time
    avg_speed, _ = compute_eta(archive_elapsed, archive_completed_bytes, archive_total_bytes)

    print(
        f"[+] Done: {output_csv.name} | "
        f"{archive_total_files} files | "
        f"{format_bytes(archive_total_bytes)} | "
        f"avg {format_bytes(avg_speed)}/s | "
        f"time {format_duration(archive_elapsed)}"
    )

    return archive_total_bytes


# ==========================================================
# MAIN
# ==========================================================
def main() -> None:
    if not SEVENZIP_EXE.is_file():
        raise FileNotFoundError(f"7z not found: {SEVENZIP_EXE}")

    archive_files = find_archive_files_in_script_folder()

    if not archive_files:
        print(f"No ZIP or RAR files found in script folder: {SCRIPT_DIR}")
        return

    print(f"Scanning archives in: {SCRIPT_DIR}")
    print("Pre-scanning archive contents for total ETA...")

    archive_entries_map: dict[Path, list[ArchiveEntry]] = {}
    global_bytes_total_all_archives = 0

    for archive_path in archive_files:
        entries = parse_7z_paths(archive_path)
        archive_entries_map[archive_path] = entries
        global_bytes_total_all_archives += sum(entry.size for entry in entries)

    print(f"Total archives: {len(archive_files)}")
    print(f"Total bytes to hash: {format_bytes(global_bytes_total_all_archives)}")
    print(f"Per-archive workers: {HASH_MAX_WORKERS}")

    global_start_time = time.perf_counter()
    global_bytes_done_before_archive = 0

    for archive_path in archive_files:
        archive_bytes_done = process_archive(
            archive_path=archive_path,
            entries=archive_entries_map[archive_path],
            global_bytes_done_before_archive=global_bytes_done_before_archive,
            global_bytes_total_all_archives=global_bytes_total_all_archives,
            global_start_time=global_start_time,
        )
        global_bytes_done_before_archive += archive_bytes_done

    total_elapsed = time.perf_counter() - global_start_time
    avg_speed, _ = compute_eta(total_elapsed, global_bytes_done_before_archive, global_bytes_total_all_archives)

    print()
    print("All done.")
    print(f"Processed archives: {len(archive_files)}")
    print(f"Total hashed: {format_bytes(global_bytes_done_before_archive)}")
    print(f"Average speed: {format_bytes(avg_speed)}/s")
    print(f"Total time: {format_duration(total_elapsed)}")


if __name__ == "__main__":
    main()