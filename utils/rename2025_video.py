# Renaming folders and files in 2025 video data
#
# Raw file name format on NAS:
#   {number}_{STATION}_{(IP_ADDRESS)}_{DATE}_{TIME}_{ID}.{ext}
# Target file name format:
#   Auklab1_{STATION}_{DATE}_{TIME}.{ext}
#
# Example:
#   12_BONDEN3_(192.168.1.128)_2025-05-16_04.00.00_7823.mp4
#   -> Auklab1_BONDEN3_2025-05-16_04.00.00.mp4
#
# Usage:
#   python rename2025_video.py            # dry-run (safe preview, no files changed)
#   python rename2025_video.py --execute  # apply renames

import re
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler("rename2025_video.log"),
        logging.StreamHandler(),
    ],
)

vid_path_2025 = Path("../../../../../../mnt/BSP_NAS2_vol4/Video/Video2025/")

# Maps the clean station name to its corresponding raw NAS folder name
# (station name + camera IP address suffix as it appears on the NAS).
# Key   = desired clean station name (used in renamed files/folders)
# Value = actual folder name on NAS (with IP suffix)
name_aliases_2025 = {
    "BJORN3TRI3_SCALE":  "BJORN3TRI3_SCALE_ (192.168.1.110)",
    "FAR3_SCALE":         "FAR3_SCALE_(192.168.1.161)",
    "FAR6BONDEN6_SCALE":  "FAR6BONDEN6_SCALE_(192.168.1.147)",
    "TRI2_SCALE":         "TRI2_SCALE _(192.168.1.161)",
    "TRI5_SCALE":         "TRI5_SCALE_(192.168.1.161)",
    "BONDEN3":            "BONDEN3_(192.168.1.128)",
    # TODO: fill in IP addresses for remaining 2025 stations once known:
    # "BONDEN1":            "BONDEN1_(192.168.1.XXX)",
    # "FAR8D_HOLK":         "FAR8D_HOLK_(192.168.1.XXX)",
    # "BONDEN3FAR3_SCALE":  "BONDEN3FAR3_SCALE_(192.168.1.XXX)",
    # "FAR6BONDEN6":        "FAR6BONDEN6_(192.168.1.XXX)",
}

# Inverted lookup: raw NAS folder name -> clean station name
_folder_to_clean = {v: k for k, v in name_aliases_2025.items()}

# Regex that parses raw video file names:
#   {num}_{STATION}_{(IP)}_{DATE}_{TIME}_{ID}.{ext}
_FILE_RE = re.compile(
    r"^(\d+)_(.+?)_\((\d{1,3}(?:\.\d{1,3}){3})\)_(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2}\.\d{2})_(\d+)\.(\w+)$"
)

# Regex that detects folder names with a trailing IP address in parentheses
_FOLDER_IP_RE = re.compile(r"^(.+?)[ _]+\((\d{1,3}(?:\.\d{1,3}){3})\)\s*$")


def _clean_folder_name(raw_name: str) -> str:
    """Return the clean station name for a raw NAS folder name.

    Looks up in _folder_to_clean first (exact match); if not found, strips the
    IP suffix detected by regex (fallback for stations not yet listed in the dict).
    Returns raw_name unchanged if no IP suffix is present.
    """
    if raw_name in _folder_to_clean:
        return _folder_to_clean[raw_name]
    m = _FOLDER_IP_RE.match(raw_name)
    if m:
        return m.group(1).rstrip("_ ")
    return raw_name


def rename_file(file_path: Path, dry_run: bool = True) -> Optional[Path]:
    """Rename one raw video file to the Auklab1_… format.

    Strips the leading numeric prefix, the IP address token, and the trailing
    numeric ID; adds the ``Auklab1_`` prefix.

    Returns the new Path on success; None if the file name does not match the
    expected raw pattern or if the target already exists (actual-rename mode).
    """
    m = _FILE_RE.match(file_path.name)
    if not m:
        return None

    _num, station, _ip, date, time_str, _id, ext = m.groups()
    new_name = f"Auklab1_{station}_{date}_{time_str}.{ext}"
    new_path = file_path.parent / new_name

    if dry_run:
        logging.info(f"[DRY-RUN] FILE  {file_path.name!r}  ->  {new_name!r}")
        return new_path

    if new_path.exists():
        logging.warning(f"SKIP (target exists): FILE  {file_path.name!r}  ->  {new_name!r}")
        return None

    file_path.rename(new_path)
    logging.info(f"RENAMED  FILE  {file_path.name!r}  ->  {new_name!r}")
    return new_path


def rename_folder(folder_path: Path, dry_run: bool = True) -> Path:
    """Rename a raw station folder (strip the IP address suffix).

    Returns the path to use when walking the folder's contents: the new path
    after an actual rename, or the original path when dry-running or when no
    renaming is needed.
    """
    clean = _clean_folder_name(folder_path.name)
    if clean == folder_path.name:
        return folder_path  # nothing to change

    new_path = folder_path.parent / clean

    if dry_run:
        logging.info(f"[DRY-RUN] DIR   {folder_path.name!r}  ->  {clean!r}")
        return folder_path  # walk original path in dry-run

    if new_path.exists():
        logging.warning(f"SKIP (target exists): DIR   {folder_path.name!r}  ->  {clean!r}")
        return folder_path

    folder_path.rename(new_path)
    logging.info(f"RENAMED  DIR   {folder_path.name!r}  ->  {clean!r}")
    return new_path


def run_rename(base_path: Path, dry_run: bool = True) -> None:
    """Walk *base_path* and rename all station folders and their video files.

    Expected directory layout::

        base_path/
          {STATION_(IP)}/          <- station folder (renamed here)
            {YYYY-MM-DD}/          <- date sub-folder
              {num}_{STATION}_{(IP)}_{DATE}_{TIME}_{ID}.mp4

    Run with ``dry_run=True`` (the default) first to preview changes without
    touching any files on disk.
    """
    if not base_path.exists():
        logging.error(f"Base path does not exist: {base_path}")
        return

    logging.info(f"{'[DRY-RUN] ' if dry_run else ''}Starting rename in {base_path}")

    for station_dir in sorted(base_path.iterdir()):
        if not station_dir.is_dir():
            continue

        # Rename the station-level folder (removes IP suffix)
        walk_dir = rename_folder(station_dir, dry_run=dry_run)

        # Walk date sub-folders and rename individual video files
        for sub in sorted(walk_dir.iterdir()):
            if sub.is_dir():
                for file_path in sorted(sub.iterdir()):
                    if file_path.is_file():
                        rename_file(file_path, dry_run=dry_run)
            elif sub.is_file():
                rename_file(sub, dry_run=dry_run)

    logging.info(f"{'[DRY-RUN] ' if dry_run else ''}Rename pass complete.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Rename 2025 NAS video folders and files to the clean Auklab1_… format.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply renames (default: dry-run only — no files are changed).",
    )
    args = parser.parse_args()

    run_rename(vid_path_2025, dry_run=not args.execute)
    if not args.execute:
        print(
            "\nThis was a DRY-RUN — no files were changed.\n"
            "Review the output above, then re-run with --execute to apply."
        )
