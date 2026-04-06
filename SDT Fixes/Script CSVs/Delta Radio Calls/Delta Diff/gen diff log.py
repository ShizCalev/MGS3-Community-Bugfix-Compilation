from __future__ import annotations

import tempfile
from pathlib import Path


DELTA_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Script CSVs\Delta Radio Calls"
)
SP_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Script CSVs\Radio Calls\sp\codec\_bp"
)
ISOLATED_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Script CSVs\Delta Diff\Isolated"
)
FR_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Script CSVs\Radio Calls\fr\codec\_bp"
)
MC_TO_DELTA_DIFF_ROOT = Path(
    r"C:\Development\Git\Afevis-MGS3-Bugfix-Compilation\SDT Fixes\Script CSVs\Delta Diff\MC to Delta Diff"
)


def pause_and_exit(code: int = 0) -> None:
    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass
    raise SystemExit(code)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_lines_preserve(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def canonical_match_key(line: str) -> str:
    stripped = line.rstrip("\r\n")

    if stripped.startswith("0x"):
        comma_index = stripped.find(",")
        if comma_index != -1:
            hex_part = stripped[2:comma_index]
            if hex_part and all(ch in "0123456789abcdefABCDEF" for ch in hex_part):
                return stripped[comma_index + 1 :]

    return stripped


def trim_after_last_quote_newline_quote(text: str) -> str:
    marker = "\"\n\""
    last_index = text.rfind(marker)
    if last_index == -1:
        return text
    return text[: last_index + len(marker)]


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding=encoding,
        newline="",
        delete=False,
        dir=str(path.parent),
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)
        tmp_file.write(content)

    tmp_path.replace(path)


def remove_empty_dirs(root: Path) -> None:
    if not root.exists():
        return

    for folder in sorted(
        (p for p in root.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        try:
            next(folder.iterdir())
        except StopIteration:
            folder.rmdir()

    try:
        next(root.iterdir())
    except StopIteration:
        root.rmdir()


def build_isolated_from_sp() -> tuple[int, int, int, int]:
    if not DELTA_ROOT.is_dir():
        print(f'[Error] Delta root does not exist: "{DELTA_ROOT}"')
        pause_and_exit(1)

    if not SP_ROOT.is_dir():
        print(f'[Error] SP root does not exist: "{SP_ROOT}"')
        pause_and_exit(1)

    ISOLATED_ROOT.mkdir(parents=True, exist_ok=True)

    delta_csvs = sorted(DELTA_ROOT.rglob("*.csv"))
    if not delta_csvs:
        print("[Info] No delta CSVs found.")
        remove_empty_dirs(ISOLATED_ROOT)
        return 0, 0, 0, 0

    processed = 0
    written = 0
    skipped_missing_sp = 0
    removed_empty_outputs = 0

    for delta_csv in delta_csvs:
        rel_path = delta_csv.relative_to(DELTA_ROOT)
        sp_csv = SP_ROOT / rel_path
        out_csv = ISOLATED_ROOT / rel_path

        processed += 1

        if not sp_csv.is_file():
            skipped_missing_sp += 1
            print(f"[Isolated Skip Missing SP] {rel_path.as_posix()}")
            continue

        delta_text = normalize_newlines(delta_csv.read_text(encoding="utf-8-sig"))
        sp_text = normalize_newlines(sp_csv.read_text(encoding="utf-8-sig"))

        delta_lines = split_lines_preserve(delta_text)
        sp_lines = split_lines_preserve(sp_text)

        sp_keys = set()
        for line in sp_lines:
            sp_keys.add(canonical_match_key(line))

        kept_lines: list[str] = []
        for line in delta_lines:
            if canonical_match_key(line) in sp_keys:
                continue
            kept_lines.append(line)

        output_text = "".join(kept_lines)
        output_text = trim_after_last_quote_newline_quote(output_text)

        if output_text:
            atomic_write_text(out_csv, output_text, encoding="utf-8")
            written += 1
            print(f"[Isolated Wrote] {rel_path.as_posix()}")
        else:
            if out_csv.exists():
                out_csv.unlink()
            removed_empty_outputs += 1
            print(f"[Isolated Empty] {rel_path.as_posix()}")

    remove_empty_dirs(ISOLATED_ROOT)
    return processed, written, skipped_missing_sp, removed_empty_outputs


def build_mc_to_delta_diff_from_fr() -> tuple[int, int, int, int]:
    if not ISOLATED_ROOT.is_dir():
        print(f'[Error] Isolated root does not exist: "{ISOLATED_ROOT}"')
        pause_and_exit(1)

    if not FR_ROOT.is_dir():
        print(f'[Error] FR root does not exist: "{FR_ROOT}"')
        pause_and_exit(1)

    MC_TO_DELTA_DIFF_ROOT.mkdir(parents=True, exist_ok=True)

    isolated_csvs = sorted(ISOLATED_ROOT.rglob("*.csv"))
    if not isolated_csvs:
        print("[Info] No isolated CSVs found.")
        remove_empty_dirs(MC_TO_DELTA_DIFF_ROOT)
        return 0, 0, 0, 0

    processed = 0
    written = 0
    skipped_missing_fr = 0
    removed_empty_outputs = 0

    for isolated_csv in isolated_csvs:
        rel_path = isolated_csv.relative_to(ISOLATED_ROOT)
        fr_csv = FR_ROOT / rel_path
        out_csv = MC_TO_DELTA_DIFF_ROOT / rel_path

        processed += 1

        if not fr_csv.is_file():
            skipped_missing_fr += 1
            print(f"[MC->Delta Skip Missing FR] {rel_path.as_posix()}")
            continue

        isolated_text = normalize_newlines(isolated_csv.read_text(encoding="utf-8-sig"))
        fr_text = normalize_newlines(fr_csv.read_text(encoding="utf-8-sig"))

        isolated_lines = split_lines_preserve(isolated_text)
        fr_lines = split_lines_preserve(fr_text)

        isolated_keys = set()
        for line in isolated_lines:
            isolated_keys.add(canonical_match_key(line))

        kept_lines: list[str] = []
        for line in fr_lines:
            if canonical_match_key(line) in isolated_keys:
                continue
            kept_lines.append(line)

        output_text = "".join(kept_lines)
        output_text = trim_after_last_quote_newline_quote(output_text)

        if output_text:
            atomic_write_text(out_csv, output_text, encoding="utf-8")
            written += 1
            print(f"[MC->Delta Wrote] {rel_path.as_posix()}")
        else:
            if out_csv.exists():
                out_csv.unlink()
            removed_empty_outputs += 1
            print(f"[MC->Delta Empty] {rel_path.as_posix()}")

    remove_empty_dirs(MC_TO_DELTA_DIFF_ROOT)
    return processed, written, skipped_missing_fr, removed_empty_outputs


def main() -> None:
    isolated_processed, isolated_written, isolated_skipped, isolated_empty = build_isolated_from_sp()
    mc_processed, mc_written, mc_skipped, mc_empty = build_mc_to_delta_diff_from_fr()

    print("\nDone.\n")

    print("Stage 1: Delta -> Isolated")
    print(f"Delta CSVs processed: {isolated_processed}")
    print(f"Output CSVs written: {isolated_written}")
    print(f"Missing SP CSVs skipped: {isolated_skipped}")
    print(f"Empty outputs removed/not written: {isolated_empty}")
    print()

    print("Stage 2: FR -> MC to Delta Diff")
    print(f"Isolated CSVs processed: {mc_processed}")
    print(f"Output CSVs written: {mc_written}")
    print(f"Missing FR CSVs skipped: {mc_skipped}")
    print(f"Empty outputs removed/not written: {mc_empty}")

    pause_and_exit(0)


if __name__ == "__main__":
    main()