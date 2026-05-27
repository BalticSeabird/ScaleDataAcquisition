#!/usr/bin/env python3
"""
Nightly Weight Sensor Monitoring Script
Monitors new .db files, runs processing pipeline, and generates daily reports
"""

import sys
from pathlib import Path
from datetime import datetime
import yaml
import pandas as pd
import json
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = Path("/home/bsp/git/ScaleDataAcquisition/")
SCRIPT_DIR = PROJECT_ROOT / "reporting"

#SCRIPT_DIR = Path(__file__).resolve().parent
from nightly_check_weight_data import analyze_weight_files as check_weight_data
from nightly_report_generator import generate_comprehensive_report

CONFIG_FILE = PROJECT_ROOT / "config/nightly_monitor_config.yaml"
PROCESSED_FILES_FILE = PROJECT_ROOT / "config/nightly_monitor_processed.json"


def load_config() -> dict:
    """Load configuration from YAML file"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def load_scale_names() -> pd.DataFrame:
    """Load scale name lookup from CSV"""
    csv_path = PROJECT_ROOT / "config/ScaleSystemNames.csv"
    if not csv_path.exists():
        print(f"Warning: Scale names CSV not found: {csv_path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path, sep=";")
        # Parse dates if present
        if "Startdate" in df.columns:
            df["Startdate"] = pd.to_datetime(df["Startdate"], errors='coerce')
        if "Enddate" in df.columns:
            df["Enddate"] = pd.to_datetime(df["Enddate"], errors='coerce')
        return df
    except Exception as e:
        print(f"Error loading scale names: {e}")
        return pd.DataFrame()


def load_processed_files() -> set:
    """Load the set of already-processed database files"""
    if PROCESSED_FILES_FILE.exists():
        with open(PROCESSED_FILES_FILE) as f:
            data = json.load(f)
            return set(data.get("processed_files", []))
    return set()


def save_processed_files(processed: set) -> None:
    """Save the set of processed database files"""
    with open(PROCESSED_FILES_FILE, "w") as f:
        json.dump({"processed_files": sorted(list(processed))}, f, indent=2)


def resolve_weightlog_dirs(config: dict) -> List[Path]:
    """Return configured weightlog directories (supports legacy single-dir key)."""
    paths_cfg = config.get("paths", {})

    # Preferred key: a list of directories.
    configured_dirs = paths_cfg.get("weightlog_dirs")
    if isinstance(configured_dirs, str):
        configured_dirs = [configured_dirs]
    elif configured_dirs is None:
        configured_dirs = []

    # Backward compatibility: single directory key.
    legacy_dir = paths_cfg.get("weightlog_dir")
    if legacy_dir:
        configured_dirs.append(legacy_dir)

    # De-duplicate while preserving order.
    unique_dirs = []
    seen = set()
    for dir_value in configured_dirs:
        if dir_value not in seen:
            seen.add(dir_value)
            unique_dirs.append(Path(dir_value))

    return unique_dirs


def db_file_identity(db_file: Path) -> str:
    """Build a stable ID for processed-file tracking across nested directories."""
    try:
        return str(db_file.resolve())
    except OSError:
        return str(db_file)


def get_new_db_files(config: dict) -> List[Path]:
    """Find .db files that haven't been processed yet (recursive, multi-directory)."""
    weightlog_dirs = resolve_weightlog_dirs(config)
    if not weightlog_dirs:
        print("Warning: no weightlog directories configured")
        return []

    existing_dirs = []
    for directory in weightlog_dirs:
        if directory.exists():
            existing_dirs.append(directory)
        else:
            print(f"Warning: weightlog directory not found: {directory}")

    if not existing_dirs:
        return []

    # Get all .db files recursively from each configured directory.
    all_files_by_id = {}
    for directory in existing_dirs:
        for db_file in directory.rglob("*.db"):
            all_files_by_id[db_file_identity(db_file)] = db_file

    all_files = list(all_files_by_id.values())
    if not all_files:
        print("No .db files found")
        return []

    # Load previously processed files
    processed_files = load_processed_files()

    # Find new files (not in processed list). Keep compatibility with older entries
    # that tracked only file names.
    new_files = [
        f for f in all_files
        if db_file_identity(f) not in processed_files and f.name not in processed_files
    ]

    if new_files:
        print(f"Found {len(new_files)} new .db file(s) to process")
        for f in new_files:
            print(f"  - {f}")
    else:
        print("No new .db files found")

    return sorted(new_files)


def analyze_new_files(config: dict, db_files: List[Path]) -> Tuple[pd.DataFrame, Optional[datetime], Dict]:
    """Analyze new weight log files using lightweight nightly analysis

    Returns: (DataFrame with analysis results, date of analysis, file_info dict)
    """
    print(f"\n{'='*80}")
    print("Analyzing Weight Files")
    print(f"{'='*80}")

    try:
        df, analysis_date, file_info = check_weight_data(db_files, config)
        if df.empty:
            print("No events detected")
        else:
            print(f"✓ Detected {len(df)} total events across all files")

        # Add scale names if available
        scale_names = load_scale_names()
        if not scale_names.empty:
            df = match_scale_names(df, scale_names, analysis_date)

        return df, analysis_date, file_info
    except Exception as e:
        print(f"Error analyzing files: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), None, {}


def match_scale_names(df: pd.DataFrame, scale_names_df: pd.DataFrame, analysis_date: Optional[datetime]) -> pd.DataFrame:
    """Match DGT + cell + date to scale names from CSV

    Returns DataFrame with additional 'Cameraname' column if matches found
    """
    if df.empty or scale_names_df.empty:
        return df

    # Add camera name column (default to empty)
    df["Cameraname"] = ""

    # For each row, try to find matching camera name
    for idx, row in df.iterrows():
        dgt = row["DGT"]
        cell = row["cell"]

        # Try to match by DGT and cell, checking dates if available
        matches = scale_names_df[scale_names_df["DGT"] == dgt]
        matches = matches[matches["cell"] == cell]

        if not matches.empty:
            # If date columns exist, check date range
            if "Startdate" in scale_names_df.columns and "Enddate" in scale_names_df.columns:
                event_date = row.get("Event_start_time")
                if event_date:
                    event_date = pd.to_datetime(event_date)
                    # Filter by date range
                    matches = matches[
                        (matches["Startdate"] <= event_date) &
                        (matches["Enddate"] >= event_date)
                    ]

            # If still have matches, use first one
            if not matches.empty and "Cameraname" in matches.columns:
                df.at[idx, "Cameraname"] = matches.iloc[0]["Cameraname"]

    return df


def generate_report(config: dict, df: pd.DataFrame, report_date: Optional[datetime] = None) -> str:
    """Generate a text report summarizing the day's data

    Args:
        config: Configuration dictionary
        df: DataFrame with analysis results
        report_date: Optional date to use in report (defaults to today)
    """
    if report_date is None:
        report_date = datetime.now()

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append(f"WEIGHT SENSOR DAILY REPORT - {report_date.strftime('%Y-%m-%d')}")
    report_lines.append("=" * 80)

    if df.empty:
        report_lines.append("\nNo events detected.")
        return "\n".join(report_lines)

    report_lines.append(f"\nReport Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Data Date: {report_date.strftime('%Y-%m-%d')}")

    # Overall stats
    report_lines.append("\n" + "-" * 80)
    report_lines.append("OVERALL STATISTICS")
    report_lines.append("-" * 80)
    report_lines.append(f"Total events detected: {len(df)}")

    events_with_weights = df[df["weight_median"].notna()]
    if len(events_with_weights) > 0:
        report_lines.append(
            f"Events with valid weights: {len(events_with_weights)} "
            f"({100*len(events_with_weights)/len(df):.1f}%)"
        )
        report_lines.append(f"Average bird weight: {events_with_weights['weight_median'].mean():.2f} kg")
        report_lines.append(f"Weight range: {events_with_weights['weight_median'].min():.2f} - "
                          f"{events_with_weights['weight_median'].max():.2f} kg")

    # Quality summary
    if "quality_mark" in df.columns:
        report_lines.append("\nQuality Distribution:")
        quality_names = {1: "Excellent", 2: "Good", 3: "Fair", 4: "Poor"}
        for mark in [1, 2, 3, 4]:
            count = (df["quality_mark"] == mark).sum()
            if count > 0:
                pct = 100 * count / len(df)
                report_lines.append(f"  {quality_names[mark]:<12}: {count:>4} ({pct:>5.1f}%)")

    # Per DGT and Cell Summary
    report_lines.append("\n" + "-" * 80)
    report_lines.append("SUMMARY BY DGT AND CELL")
    report_lines.append("-" * 80)

    dgts = config["dgts"]
    cells_per_dgt = config["cells_per_dgt"]

    for dgt in dgts:
        dgt_data = df[df["DGT"] == dgt]
        if len(dgt_data) == 0:
            report_lines.append(f"\n{dgt}: No events")
            continue

        report_lines.append(f"\n{dgt}:")
        total_events_dgt = len(dgt_data)
        report_lines.append(f"  Total events: {total_events_dgt}")

        for cell in range(1, cells_per_dgt + 1):
            cell_data = dgt_data[dgt_data["cell"] == cell]
            if len(cell_data) == 0:
                report_lines.append(f"    Cell {cell}: No events")
                continue

            event_count = len(cell_data)
            cell_weights = cell_data[cell_data["weight_median"].notna()]

            # Get scale name if available
            scale_name = ""
            if "Cameraname" in cell_data.columns and not cell_data["Cameraname"].iloc[0]:
                scale_name = ""
            elif "Cameraname" in cell_data.columns:
                scale_name = cell_data["Cameraname"].iloc[0]

            line = f"    Cell {cell}"
            if scale_name:
                line += f" ({scale_name})"
            line += f": {event_count} events"

            if len(cell_weights) > 0:
                avg_weight = cell_weights["weight_median"].mean()
                line += f" | Avg weight: {avg_weight:.2f} kg"

                if "quality_mark" in df.columns:
                    good = (cell_weights["quality_mark"] <= 2).sum()
                    line += f" | Good quality: {good}/{len(cell_weights)}"

            report_lines.append(line)

    # Sensor health check
    report_lines.append("\n" + "-" * 80)
    report_lines.append("SENSOR HEALTH CHECK")
    report_lines.append("-" * 80)

    if "tare_before_var" in df.columns and "tare_after_var" in df.columns:
        high_tare_var = (
            ((df["tare_before_var"] > 0.001) | (df["tare_after_var"] > 0.001)).sum()
        )
        if high_tare_var > 0:
            report_lines.append(f"⚠️  {high_tare_var} events with high baseline noise")

    if "weight_var" in df.columns:
        high_weight_var = (df["weight_var"] > 0.001).sum()
        if high_weight_var > 0:
            report_lines.append(f"⚠️  {high_weight_var} events with high signal noise")

    nan_weights = df["weight_median"].isna().sum()
    if nan_weights > 0:
        report_lines.append(f"⚠️  {nan_weights} events without weight data")

    if nan_weights == 0 and "tare_before_var" in df.columns:
        high_tare_var = ((df["tare_before_var"] > 0.001) | (df["tare_after_var"] > 0.001)).sum()
        if high_tare_var == 0 and "weight_var" in df.columns:
            high_weight_var = (df["weight_var"] > 0.001).sum()
            if high_weight_var == 0:
                report_lines.append("✓ All sensors functioning normally")

    report_lines.append("\n" + "=" * 80)

    return "\n".join(report_lines)


def parse_db_report_metadata(db_name: str) -> Tuple[Optional[datetime], str]:
    """Extract report date and DGT name from a DB filename.

    Expected filename format: YYYYMMDD_dgtX.db
    """
    stem = Path(db_name).stem
    parts = stem.split("_", 1)

    report_date = None
    dgt_name = "unknown"

    if parts:
        try:
            report_date = datetime.strptime(parts[0], "%Y%m%d")
        except ValueError:
            report_date = None

    if len(parts) > 1 and parts[1]:
        dgt_name = parts[1]

    return report_date, dgt_name


def save_report(
    config: dict,
    report_text: str,
    report_date: Optional[datetime] = None,
    dgt_name: str = "unknown",
) -> Path:
    """Save the report to file using actual data date

    Args:
        config: Configuration dictionary
        report_text: Report text to save
        report_date: Optional date for filename (defaults to today)
        dgt_name: DGT identifier for filename
    """
    if report_date is None:
        report_date = datetime.now()

    report_dir = Path(config["paths"]["report_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)

    filename = report_dir / f"weight_report_{report_date.strftime('%Y-%m-%d')}_{dgt_name}.txt"
    with open(filename, "w") as f:
        f.write(report_text)

    print(f"\nReport saved to: {filename}")
    return filename


def main():
    """Main monitoring function"""
    try:
        config = load_config()
        print(f"Configuration loaded from: {CONFIG_FILE}")

        # Find new files
        new_files = get_new_db_files(config)

        if not new_files:
            print("No new files to process")
            return

        print(f"Processing {len(new_files)} file(s)")

        processed_files = load_processed_files()
        generated_count = 0
        processed_count = 0

        for db_file in new_files:
            db_name = db_file.name
            report_date, dgt_name = parse_db_report_metadata(db_name)

            try:
                # Analyze and report on one database file at a time so progress is checkpointed.
                file_df, file_analysis_date, file_info = analyze_new_files(config, [db_file])

                if report_date is None:
                    report_date = file_analysis_date

                # Fallback to data timestamps if filename parsing fails.
                if report_date is None and not file_df.empty and "Event_start_time" in file_df.columns:
                    report_date = pd.to_datetime(file_df["Event_start_time"].min()).to_pydatetime()

                per_file_info = {db_name: file_info.get(db_name, (None, None))}
                report_text = generate_comprehensive_report(config, file_df, report_date, per_file_info)
                save_report(config, report_text, report_date, dgt_name)

                processed_files.add(db_file_identity(db_file))
                save_processed_files(processed_files)

                generated_count += 1
                processed_count += 1
                print(f"✓ Checkpointed {db_name}")
            except Exception as file_error:
                print(f"Error processing {db_name}: {file_error}")
                import traceback
                traceback.print_exc()
                raise

        if generated_count > 0:
            print(f"✓ Generated {generated_count} report file(s) (one per .db file)")

        print(f"✓ Marked {processed_count} file(s) as processed")

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
