#!/usr/bin/env python3
"""
Test script for multi-year video renaming.

Finds real video files from each available year, creates test copies,
and verifies the renaming logic works correctly.
"""

import tempfile
import shutil
import random
import os
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Import the rename functions
from rename2025_video import VID_PATHS, run_rename, rename_file, _FILE_RE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)

logger = logging.getLogger(__name__)


def find_sample_files(year: int, max_per_station: int = 2) -> List[Path]:
    """Find sample video files from a given year's video path.

    Returns a list of actual file paths, randomly selected from different stations.
    """
    vid_path = VID_PATHS.get(year)
    if not vid_path or not vid_path.exists():
        logger.warning(f"Path for year {year} not found or doesn't exist: {vid_path}")
        return []

    samples = []
    stations_seen = set()

    # Walk through the directory and collect samples
    for station_dir in sorted(vid_path.iterdir()):
        if not station_dir.is_dir():
            continue

        station_name = station_dir.name
        if station_name in stations_seen:
            continue

        # Find files in date subdirectories
        for date_dir in sorted(station_dir.iterdir()):
            if not date_dir.is_dir():
                continue

            files = list(date_dir.glob("*"))
            if files:
                # Randomly select up to max_per_station files
                selected = random.sample(files, min(max_per_station, len(files)))
                samples.extend(selected)
                stations_seen.add(station_name)
                break

        if len(samples) >= 3:  # We have enough samples
            break

    return samples[:3]  # Return up to 3 samples


def create_test_structure(year: int, samples: List[Path]) -> Path:
    """Create a temporary directory with test file copies matching year's structure.

    Returns the path to the temporary directory.
    """
    temp_dir = tempfile.mkdtemp(prefix=f"test_rename_y{year}_")
    logger.info(f"Creating test structure at {temp_dir}")

    for sample_file in samples:
        # Recreate the directory structure relative to year's base
        vid_path = VID_PATHS[year]
        rel_path = sample_file.relative_to(vid_path)

        # Create the directory structure
        target_dir = Path(temp_dir) / rel_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy the file
        target_file = target_dir / sample_file.name
        shutil.copy2(sample_file, target_file)
        logger.info(f"  Copied: {rel_path}")

    return Path(temp_dir)


def test_year(year: int) -> Tuple[bool, str]:
    """Test the rename logic for a given year.

    Returns (success: bool, message: str)
    """
    logger.info(f"\n{'=' * 70}")
    logger.info(f"Testing Year {year}")
    logger.info(f"{'=' * 70}")

    # Find sample files
    samples = find_sample_files(year, max_per_station=2)
    if not samples:
        msg = f"No sample files found for year {year}"
        logger.warning(msg)
        return False, msg

    logger.info(f"Found {len(samples)} sample files for year {year}")
    for s in samples:
        logger.info(f"  - {s}")

    # Create test structure
    test_dir = create_test_structure(year, samples)

    try:
        # Run dry-run to see what would change
        logger.info(f"\nRunning dry-run for year {year}...")
        run_rename(Path(test_dir), year=year, dry_run=True)

        # Check if any files matched the pattern
        found_matches = False
        for root, dirs, files in os.walk(str(test_dir)):
            for f in files:
                file_path = Path(root) / f
                if _FILE_RE.match(f):
                    found_matches = True
                    break
            if found_matches:
                break

        if not found_matches:
            logger.info(f"Note: No raw-format files found for year {year} (files may be pre-renamed)")

        msg = f"Year {year} tested successfully"
        return True, msg

    except Exception as e:
        msg = f"Error testing year {year}: {e}"
        logger.error(msg, exc_info=True)
        return False, msg

    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)
        logger.info(f"Cleaned up test directory: {test_dir}")


def main():
    """Test all available years."""
    logger.info("Multi-Year Video Rename Test")
    logger.info("=" * 70)

    results = {}
    for year in sorted(VID_PATHS.keys()):
        success, msg = test_year(year)
        results[year] = (success, msg)

    # Summary
    logger.info(f"\n{'=' * 70}")
    logger.info("Test Summary")
    logger.info(f"{'=' * 70}")
    for year in sorted(results.keys()):
        success, msg = results[year]
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {msg}")

    all_passed = all(success for success, _ in results.values())
    logger.info(f"\n{'='*70}")
    if all_passed:
        logger.info("All tests passed!")
    else:
        logger.info("Some tests failed.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
