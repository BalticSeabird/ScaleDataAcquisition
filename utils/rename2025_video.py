# Renaming folders and files in video data from multiple years
#
# Raw file name format on NAS:
#   {number}_{STATION}_{(IP_ADDRESS)}_{DATE}_{TIME}_{ID}.{ext}
# Target file name format:
#   Auklab1_{MAPPED_STATION}_{DATE}_{TIME}.{ext}
#
# Example:
#   12_BONDEN3_(192.168.1.128)_2025-05-16_04.00.00_7823.mp4
#   -> Auklab1_BONDEN3_2025-05-16_04.00.00.mp4
#
# Usage:
#   python rename2025_video.py            # dry-run (safe preview, no files changed)
#   python rename2025_video.py --execute  # apply renames
#   python rename2025_video.py --year 2024  # rename 2024 video data
#   python rename2025_video.py --year 2023 --execute  # apply renames for 2023

import re
import logging
from pathlib import Path
from typing import Optional, Dict
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler("rename_video.log"),
        logging.StreamHandler(),
    ],
)

# Paths to video data for different years
VID_PATHS = {
    2025: Path("../../../../../../mnt/BSP_NAS2_vol4/Video/Video2025/"),
    2024: Path("../../../../../../mnt/BSP_NAS2/Video/Video2024/"),
    2023: Path("../../../../../../mnt/BSP_NAS2/Video/Video2023/"),
}

# Station name mappings for different years
# Maps old station names (with/without IP) to new clean station names
STATION_MAPS = {
    2025: {
        "ROST4_(192.168.1.175)": "ROST4",
        "TRI4L_(192.168.1.198)": "TRI4L",
    },
    2024: {},  # 2024 already has clean names
    2023: {},  # 2023 has different naming format
}

# Regex that parses raw video file names:
#   {num}_{STATION}_{(IP)}_{DATE}_{TIME}_{ID}.{ext}

# Regex that parses raw video file names:
#   {num}_{STATION}_{(IP)}_{DATE}_{TIME}_{ID}.{ext}
_FILE_RE = re.compile(
    r"^(?:(?P<prefix>\d+)_)?(?P<station>.+?)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}\.\d{2}\.\d{2})(?:_(?P<seq>\d+))?\.(?P<ext>\w+)$"
)

# Regex that strips trailing IP address from station names
_IP_SUFFIX_RE = re.compile(r"\s*[_]?\s*\((\d{1,3}(?:\.\d{1,3}){3})\)\s*$")


def _strip_ip_suffix(name: str) -> str:
    """Remove IP address suffix from station name."""
    return _IP_SUFFIX_RE.sub("", name.strip())


def _resolve_station_name(station: str, year: int) -> Optional[str]:
    """Resolve old station name to new clean name using STATION_MAPS[year].

    Tries:
    1. Exact match in STATION_MAPS[year]
    2. Match after stripping IP suffix
    3. Returns mapped name or None if not found
    """
    if year not in STATION_MAPS:
        return None

    station_map = STATION_MAPS[year]
    station = station.strip()

    # Try exact match first
    if station in station_map:
        return station_map[station]

    # Try without IP suffix
    station_no_ip = _strip_ip_suffix(station)
    if station_no_ip in station_map:
        return station_map[station_no_ip]

    # Not found
    return None


def _clean_folder_name(raw_name: str, year: int) -> Optional[str]:
    """Return the clean station name for a raw NAS folder name, or None if unmapped."""
    return _resolve_station_name(raw_name, year)


def rename_file(file_path: Path, year: int, dry_run: bool = True) -> Optional[Path]:
    """Rename one raw video file to the Auklab1_… format.

    Extracts station name, date, and time from filename; maps station name using
    STATION_MAPS[year]; creates new filename: Auklab1_{MAPPED_STATION}_{DATE}_{TIME}.{ext}

    Returns the new Path on success; None if the file name does not match the
    expected raw pattern, if the station cannot be mapped, or if the target
    already exists (actual-rename mode).
    """
    m = _FILE_RE.match(file_path.name)
    if not m:
        return None

    station = m.group("station")
    mapped_station = _resolve_station_name(station, year)

    if mapped_station is None:
        logging.warning(f"UNMAPPED STATION in FILE: {file_path.name!r}  Station: {station!r}")
        return None

    date = m.group("date")
    time_str = m.group("time")
    ext = m.group("ext")

    new_name = f"Auklab1_{mapped_station}_{date}_{time_str}.{ext}"
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


def rename_folder(folder_path: Path, year: int, dry_run: bool = True) -> Path:
    """Rename a raw station folder using STATION_MAPS[year].

    Returns the path to use when walking the folder's contents: the new path
    after an actual rename, or the original path when dry-running or when no
    renaming is needed. Returns None if the folder cannot be mapped.
    """
    clean = _clean_folder_name(folder_path.name, year)
    if clean is None:
        logging.warning(f"UNMAPPED FOLDER: {folder_path.name!r}")
        return folder_path

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


def run_rename(base_path: Path, year: int, dry_run: bool = True) -> None:
    """Walk *base_path* and rename all station folders and their video files for the given year.

    Expected directory layout::

        base_path/
          {STATION_(IP)}/          <- station folder (renamed here)
            {YYYY-MM-DD}/          <- date sub-folder
              {num}_{STATION}_{(IP)}_{DATE}_{TIME}_{ID}.mp4

    Run with ``dry_run=True`` (the default) first to preview changes without
    touching any files on disk. Reports validation issues:
    - Unmapped stations
    - Naming conflicts
    - Missing files
    """
    if not base_path.exists():
        logging.error(f"Base path does not exist: {base_path}")
        return

    logging.info(f"{'[DRY-RUN] ' if dry_run else ''}Starting rename in {base_path} (Year: {year})")

    stats = defaultdict(int)
    seen_targets = defaultdict(list)  # Track target names to detect conflicts

    for station_dir in sorted(base_path.iterdir()):
        if not station_dir.is_dir():
            continue

        # Rename the station-level folder (removes IP suffix)
        walk_dir = rename_folder(station_dir, year=year, dry_run=dry_run)
        stats["folders_processed"] += 1

        # Walk date sub-folders and rename individual video files
        for sub in sorted(walk_dir.iterdir()):
            if sub.is_dir():
                for file_path in sorted(sub.iterdir()):
                    if file_path.is_file():
                        result = rename_file(file_path, year=year, dry_run=dry_run)
                        if result:
                            stats["files_processed"] += 1
                            seen_targets[result.name].append(file_path.name)
                        else:
                            stats["files_skipped"] += 1
            elif sub.is_file():
                result = rename_file(sub, year=year, dry_run=dry_run)
                if result:
                    stats["files_processed"] += 1
                    seen_targets[result.name].append(sub.name)
                else:
                    stats["files_skipped"] += 1

    # Report conflicts
    conflicts = {k: v for k, v in seen_targets.items() if len(v) > 1}
    if conflicts:
        logging.warning(f"\n!!! NAME CONFLICT DETECTED !!!")
        for target, sources in conflicts.items():
            logging.warning(f"  Target: {target!r}")
            for src in sources:
                logging.warning(f"    <- {src!r}")

    logging.info(f"{'[DRY-RUN] ' if dry_run else ''}Rename pass complete.")
    logging.info(f"Summary: {stats['files_processed']} files, {stats['folders_processed']} folders processed")
    if stats["files_skipped"] > 0:
        logging.warning(f"Skipped: {stats['files_skipped']} files (unmapped or conflicting)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Rename NAS video folders and files to the clean Auklab1_… format.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        choices=list(VID_PATHS.keys()),
        help="Year of video data to rename (default: 2025).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply renames (default: dry-run only — no files are changed).",
    )
    args = parser.parse_args()

    if args.year not in VID_PATHS:
        logging.error(f"Year {args.year} not configured. Available years: {list(VID_PATHS.keys())}")
    else:
        run_rename(VID_PATHS[args.year], year=args.year, dry_run=not args.execute)
        if not args.execute:
            print(
                "\nThis was a DRY-RUN — no files were changed.\n"
                "Review the output above, then re-run with --execute to apply."
            )
