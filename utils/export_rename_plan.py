#!/usr/bin/env python3
"""Export rename plan to CSV for manual verification before executing."""

import csv
import re
from pathlib import Path
from typing import Optional

vid_path_2025 = Path("../../../../../../mnt/BSP_NAS2_vol4/Video/Video2025/")

STATION_MAP_2025 = {
    "BONDEN3_(192.168.1.128)": "BONDEN3",
    "FAR3BONDEN3_SCALE_(192.168.1.158)": "FAR3BONDEN3_SCALE",
    "BJORN3TRI3_SCALE_ (192.168.1.110)": "BJORN3TRI3_SCALE",
    "FAR6BONDEN6_SCALE_(192.168.1.147)": "FAR6BONDEN6_SCALE",
    "FAR3_SCALE_(192.168.1.161)": "FAR3_SCALE",
    "TRI2_SCALE _(192.168.1.161)": "TRI2_SCALE",
    "TRI5_SCALE_(192.168.1.161)": "TRI5_SCALE",
    "BJORN1_(192.168.1.121)": "BJORN1",
    "BJORN2_(192.168.1.204)": "BJORN2",
    "BJORN3_(192.168.1.198)": "BJORN3",
    "BJORN4_(192.168.1.150)": "BJORN4",
    "BJORN5_(192.168.1.152)": "BJORN5",
    "BONDEN1_(192.168.1.113)": "BONDEN1",
    "BONDEN2_(192.168.1.107)": "BONDEN2",
    "BONDEN4_(192.168.1.122)": "BONDEN4",
    "BONDEN5_(192.168.1.126)": "BONDEN5",
    "BONDEN6_(192.168.1.174)": "BONDEN6",
    "FAR2L_(192.168.1.111)": "FAR2L",
    "FAR2R_(192.168.1.139)": "FAR2R",
    "FAR4L_(192.168.1.195)": "FAR4L",
    "FAR4R_(192.168.1.136)": "FAR4R",
    "FAR5L_(192.168.1.167)": "FAR5L",
    "FAR5R_(192.168.1.183)": "FAR5R",
    "IOM3_(192.168.1.162)": "IOM3",
    "OVERVIEW1_(192.168.1.160)": "OVERVIEW",
    "ROST3_(192.168.1.130)": "ROST3",
    "ROST4_(192.168.1.152)": "ROST4",
    "ROST4_(192.168.1.175)": "ROST4",
    "ROST5_(192.168.1.129)": "ROST5",
    "TRI1L_(192.168.1.170)": "TRI1L",
    "TRI1R_(192.168.1.166)": "TRI1R",
    "TRI2R_(192.168.1.134)": "TRI2R",
    "TRI4L_(192.168.1.115)": "TRI4L",
    "TRI4L_(192.168.1.198)": "TRI4L",
    "TRI4R_(192.168.1.131)": "TRI4R",
    "TRI5L_(192.168.1.143)": "TRI5L",
    "TRI5R_(192.168.1.165)": "TRI5R",
}

_IP_SUFFIX_RE = re.compile(r"\s*[_]?\s*\((\d{1,3}(?:\.\d{1,3}){3})\)\s*$")

_FILE_RE = re.compile(
    r"^(?:(?P<prefix>\d+)_)?(?P<station>.+?)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}\.\d{2}\.\d{2})(?:_(?P<seq>\d+))?\.(?P<ext>\w+)$"
)


def _strip_ip_suffix(name: str) -> str:
    """Remove IP address suffix from station name."""
    return _IP_SUFFIX_RE.sub("", name.strip())


def _resolve_station_name(station: str) -> Optional[str]:
    """Resolve old station name to new clean name using STATION_MAP_2025."""
    station = station.strip()
    if station in STATION_MAP_2025:
        return STATION_MAP_2025[station]
    station_no_ip = _strip_ip_suffix(station)
    if station_no_ip in STATION_MAP_2025:
        return STATION_MAP_2025[station_no_ip]
    return None


def export_plan(base_path: Path, out_csv: Path) -> None:
    """Export rename plan to CSV in two steps: folders first, then files with new paths.

    For files: OLD_PATH uses the NEW renamed folder (after step 1), NEW_PATH is the final name.
    This way you can apply the CSV sequentially: step 1 folders, then step 2 files.
    """
    if not base_path.exists():
        print(f"Error: Base path does not exist: {base_path}")
        return

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    # Step 1: Collect all folder renames
    print("Step 1: Collecting folder renames...")
    for station_dir in sorted(base_path.iterdir()):
        if not station_dir.is_dir():
            continue

        clean_name = _resolve_station_name(station_dir.name)
        if clean_name and clean_name != station_dir.name:
            rows.append(["FOLDER", station_dir.name, clean_name])

    # Step 2: Collect all file renames (with NEW renamed folder paths)
    print("Step 2: Collecting file renames...")
    for station_dir in sorted(base_path.iterdir()):
        if not station_dir.is_dir():
            continue

        clean_name = _resolve_station_name(station_dir.name)

        # Only process files from mapped stations
        if clean_name:
            # Get the NEW folder path (as it will be after step 1 renames)
            new_folder = station_dir.parent / clean_name

            for sub in sorted(station_dir.iterdir()):
                if sub.is_dir():
                    for file_path in sorted(sub.iterdir()):
                        if file_path.is_file() and file_path.suffix.lower() == ".mp4":
                            m = _FILE_RE.match(file_path.name)
                            if m:
                                station = m.group("station")
                                mapped_station = _resolve_station_name(station)
                                if mapped_station:
                                    date = m.group("date")
                                    time_str = m.group("time")
                                    ext = m.group("ext")
                                    new_name = f"Auklab1_{mapped_station}_{date}_{time_str}.{ext}"
                                    # OLD_PATH: Use the NEW renamed folder (after step 1)
                                    old_file_path = new_folder / sub.name / file_path.name
                                    # NEW_PATH: Same folder but with new filename
                                    new_file_path = new_folder / sub.name / new_name
                                    rows.append(["FILE", str(old_file_path), str(new_file_path)])
                elif sub.is_file() and sub.suffix.lower() == ".mp4":
                    m = _FILE_RE.match(sub.name)
                    if m:
                        station = m.group("station")
                        mapped_station = _resolve_station_name(station)
                        if mapped_station:
                            date = m.group("date")
                            time_str = m.group("time")
                            ext = m.group("ext")
                            new_name = f"Auklab1_{mapped_station}_{date}_{time_str}.{ext}"
                            # OLD_PATH: Use the NEW renamed folder (after step 1)
                            old_file_path = new_folder / sub.name
                            # NEW_PATH: Same folder with new filename
                            new_file_path = new_folder / new_name
                            rows.append(["FILE", str(old_file_path), str(new_file_path)])

    # Write CSV
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["TYPE", "OLD_PATH", "NEW_PATH"])
        writer.writerow(["# STEP 1: Rename all FOLDER entries first", "", ""])

        folder_rows = [r for r in rows if r[0] == "FOLDER"]
        file_rows = [r for r in rows if r[0] == "FILE"]

        writer.writerows(folder_rows)
        writer.writerow(["# STEP 2: Then rename all FILE entries", "", ""])
        writer.writerows(file_rows)

    print(f"\nRename plan exported to: {out_csv}")
    print(f"Total operations: {len(rows)}")
    print(f"  Step 1 - Folders: {len(folder_rows)}")
    print(f"  Step 2 - Files: {len(file_rows)}")
    print(f"\nIMPORTANT: Apply step 1 (folder renames) BEFORE step 2 (file renames)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export 2025 NAS rename plan to CSV")
    parser.add_argument(
        "--root",
        type=Path,
        default=vid_path_2025,
        help="Root directory for Video2025",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("out/rename2025_plan.csv"),
        help="Output CSV file",
    )
    args = parser.parse_args()

    export_plan(args.root, args.output)
