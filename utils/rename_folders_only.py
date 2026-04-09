#!/usr/bin/env python3
"""Rename just the ROST4 and TRI4L folders (files already renamed)."""

from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)

vid_path_2025 = Path("../../../../../../mnt/BSP_NAS2_vol4/Video/Video2025/")

folders_to_rename = [
    ("ROST4_(192.168.1.175)", "ROST4"),
    ("TRI4L_(192.168.1.198)", "TRI4L"),
]

def dry_run():
    """Show what would be renamed."""
    logging.info("[DRY-RUN] Folders to rename:")
    for old_name, new_name in folders_to_rename:
        old_path = vid_path_2025 / old_name
        new_path = vid_path_2025 / new_name
        if old_path.exists():
            logging.info(f"  {old_name!r} -> {new_name!r}")
        else:
            logging.warning(f"  FOLDER NOT FOUND: {old_name!r}")

def execute():
    """Perform the renames."""
    for old_name, new_name in folders_to_rename:
        old_path = vid_path_2025 / old_name
        new_path = vid_path_2025 / new_name
        
        if not old_path.exists():
            logging.warning(f"FOLDER NOT FOUND: {old_name!r}")
            continue
        
        if new_path.exists():
            logging.warning(f"SKIP (target exists): {old_name!r} -> {new_name!r}")
            continue
        
        old_path.rename(new_path)
        logging.info(f"RENAMED: {old_name!r} -> {new_name!r}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Rename ROST4 and TRI4L folders only")
    parser.add_argument("--execute", action="store_true", help="Apply renames (default: dry-run)")
    args = parser.parse_args()
    
    if args.execute:
        execute()
        print("\nRename complete!")
    else:
        dry_run()
        print("\nThis was a DRY-RUN — no files were changed.\nRe-run with --execute to apply.")
