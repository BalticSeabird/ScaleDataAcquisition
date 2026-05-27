#!/usr/bin/env python3
"""
Lightweight nightly analysis script
Combines event detection + weight metrics + quality scoring without database writes
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys
from datetime import datetime
from typing import Dict, Tuple, List, Optional

# Parameters (tunable)
WINDOWSIZE = 30
THRESHOLD = 0.6
TARE_LENGTH = 2500
TARE_OFFSET_BEFORE = 750
TARE_OFFSET_AFTER = 750
START_DELAY = 1000
END_DELAY = 1000

# Quality thresholds (V1 conservative)
TARE_VAR_THRESHOLD = 0.001
WEIGHT_VAR_THRESHOLD = 0.001
TARE_DRIFT_THRESHOLD = 1.0  # percent


def load_db(db_path: Path) -> Tuple[pd.DataFrame, Optional[datetime]]:
    """
    Load weight log database into DataFrame and extract the date from timestamps

    Returns: (DataFrame, date from database timestamps)
    """
    try:
        con = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])
        con.close()

        # Extract date from unix timestamp (in milliseconds)
        # Convert ms to seconds, then to datetime
        if not df.empty and "timestamp" in df.columns:
            # Timestamps are in milliseconds
            db_date = pd.to_datetime(df["timestamp"].iloc[0], unit='ms')
        else:
            db_date = None

        return df, db_date
    except Exception as e:
        print(f"Error loading {db_path.name}: {e}")
        return pd.DataFrame(), None


def find_corresponding_db(db_name: str, weightlog_roots: List[Path]) -> Optional[Path]:
    """Find the raw weight log database file"""
    for root in weightlog_roots:
        if root and root.exists():
            matches = list(root.rglob(db_name))
            if matches:
                return matches[0]
    return None


def detect_events(cell_data: pd.Series, timestamps: pd.Series) -> Tuple[List[int], List[int], List[pd.Timestamp], List[pd.Timestamp]]:
    """
    Detect events using sliding median and state machine

    Returns:
        (start_indices, end_indices, start_times, end_times)
    """
    # Apply sliding median filter
    median_vect = cell_data.rolling(WINDOWSIZE).median()

    # Determine on/off state based on threshold
    state = np.where(median_vect > THRESHOLD, 1, 0)

    # Adjust for window delay
    halfwindow = int(WINDOWSIZE / 2)
    state = np.concatenate((state[halfwindow:], np.repeat(0, halfwindow)))

    # Detect state changes
    statechange = pd.Series(state).diff().fillna(0).astype("int")

    # Extract start and end indices
    start_idx = np.where(statechange == 1)[0]
    end_idx = np.where(statechange == -1)[0]

    # Convert to timestamps
    start_times = timestamps.iloc[start_idx].values
    end_times = timestamps.iloc[end_idx].values

    return list(start_idx), list(end_idx), list(start_times), list(end_times)


def extract_weight_metrics(raw_data: pd.DataFrame, event_start: int, event_end: int, cell: int) -> Dict:
    """
    Extract weight metrics for a single event

    Returns dictionary with weight and tare metrics
    """
    cell_name = f"cell_{cell}"

    # Define time windows
    cond_event_start = raw_data["timestamp"] > event_start + START_DELAY
    cond_event_end = raw_data["timestamp"] < event_end - END_DELAY
    cond_tare_before_start = raw_data["timestamp"] >= event_start - TARE_LENGTH
    cond_tare_before_end = raw_data["timestamp"] < event_start - TARE_OFFSET_BEFORE
    cond_tare_after_start = raw_data["timestamp"] >= event_end + TARE_OFFSET_AFTER
    cond_tare_after_end = raw_data["timestamp"] < event_end + TARE_OFFSET_AFTER + TARE_LENGTH

    # Extract data windows
    data_event = raw_data[cond_event_start & cond_event_end][cell_name]
    data_before = raw_data[cond_tare_before_start & cond_tare_before_end][cell_name]
    data_after = raw_data[cond_tare_after_start & cond_tare_after_end][cell_name]

    # Calculate event duration
    event_duration_ms = event_end - event_start

    # Tare metrics
    tare_before_mean = data_before.mean() if len(data_before) > 0 else np.nan
    tare_before_var = data_before.var() if len(data_before) > 0 else np.nan
    tare_after_mean = data_after.mean() if len(data_after) > 0 else np.nan
    tare_after_var = data_after.var() if len(data_after) > 0 else np.nan

    # Tare consistency metrics
    tare_before_median = data_before.median() if len(data_before) > 0 else np.nan
    tare_after_median = data_after.median() if len(data_after) > 0 else np.nan
    tare_average = (tare_before_median + tare_after_median) / 2 if not (np.isnan(tare_before_median) or np.isnan(tare_after_median)) else np.nan

    tare_mean_diff = abs(tare_before_mean - tare_after_mean) if not (np.isnan(tare_before_mean) or np.isnan(tare_after_mean)) else np.nan
    tare_mean_diff_pct = (tare_mean_diff / (abs(tare_before_mean) + 1e-6)) * 100 if not np.isnan(tare_mean_diff) else np.nan

    # Weight metrics
    metrics = {
        "event_duration_ms": event_duration_ms,
        "event_data_points": len(data_event),
        "tare_before_points": len(data_before),
        "tare_after_points": len(data_after),
        "tare_before_mean": tare_before_mean,
        "tare_before_var": tare_before_var,
        "tare_after_mean": tare_after_mean,
        "tare_after_var": tare_after_var,
        "tare_mean_diff": tare_mean_diff,
        "tare_mean_diff_pct": tare_mean_diff_pct,
    }

    # Weight calculation
    if len(data_event) > 5:
        weight_median = data_event.median() - tare_average
        weight_var = data_event.var()
        weight_std = data_event.std()
        event_min = data_event.min()
        event_max = data_event.max()
        event_range = event_max - event_min

        # Coefficient of variation
        event_mean = data_event.mean()
        if event_mean != 0:
            signal_cv = (weight_std / abs(event_mean)) * 100
        else:
            signal_cv = np.nan

        metrics.update({
            "weight_median": weight_median,
            "weight_var": weight_var,
            "weight_std": weight_std,
            "event_min": event_min,
            "event_max": event_max,
            "event_range": event_range,
            "signal_cv_percent": signal_cv,
        })
    else:
        metrics.update({
            "weight_median": np.nan,
            "weight_var": np.nan,
            "weight_std": np.nan,
            "event_min": np.nan,
            "event_max": np.nan,
            "event_range": np.nan,
            "signal_cv_percent": np.nan,
        })

    return metrics


def assign_quality_mark(metrics: Dict) -> int:
    """
    Assign quality mark using V1 (conservative) classification

    Returns: quality mark (1=excellent, 2=good, 3=fair, 4=poor)
    """
    # Check for NaN weight
    if pd.isna(metrics.get("weight_median")):
        return 4

    # Check tare variance
    if metrics.get("tare_before_var", np.inf) > TARE_VAR_THRESHOLD:
        return 4
    if metrics.get("tare_after_var", np.inf) > TARE_VAR_THRESHOLD:
        return 4

    # Check tare consistency
    if metrics.get("tare_mean_diff_pct", np.inf) > TARE_DRIFT_THRESHOLD:
        return 4

    # Check weight variance
    if metrics.get("weight_var", np.inf) > WEIGHT_VAR_THRESHOLD:
        return 4

    # All checks passed
    return 1


def analyze_weight_file(db_path: Path, config: Optional[Dict] = None) -> Tuple[pd.DataFrame, Optional[datetime], Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """
    Analyze a single weight log file and return summary statistics

    Args:
        db_path: Path to raw weight log .db file
        config: Optional config dict with weightlog_roots

    Returns:
        (DataFrame with one row per event, analysis_date, file_start_time, file_end_time)
    """
    print(f"Analyzing {db_path.name}...", end=" ")

    # Load raw data
    df_raw, db_date = load_db(db_path)
    if df_raw.empty:
        print("No data")
        return pd.DataFrame(), db_date, None, None

    # Extract DGT and date from filename
    # Expected format: YYYYMMDD_dgtX.db
    dgt = db_path.name[9:13]
    filename_date = db_path.name[:8]

    # Use database timestamp date if available, otherwise filename
    if db_date is not None:
        analysis_date = db_date
    else:
        try:
            analysis_date = pd.to_datetime(filename_date, format='%Y%m%d')
        except:
            analysis_date = None

    # Extract file start and end times from unix timestamps
    if not df_raw.empty and "timestamp" in df_raw.columns:
        file_start_ts = df_raw["timestamp"].iloc[0]
        file_end_ts = df_raw["timestamp"].iloc[-1]
        # Convert to datetime (UTC+2 for local time)
        file_start_time = pd.Timestamp(file_start_ts, unit='ms') + pd.Timedelta(hours=2)
        file_end_time = pd.Timestamp(file_end_ts, unit='ms') + pd.Timedelta(hours=2)
    else:
        file_start_time = None
        file_end_time = None

    # Convert timestamp to datetime (UTC+2 for local time)
    ts = pd.to_datetime((1000*60*60*2) + df_raw["timestamp"], unit='ms')

    results = []

    # Process each cell (1-4)
    for cell in range(1, 5):
        cell_name = f"cell_{cell}"
        if cell_name not in df_raw.columns:
            continue

        # Detect events for this cell
        start_indices, end_indices, start_times, end_times = detect_events(
            df_raw[cell_name],
            df_raw["timestamp"]
        )

        # Process each detected event
        for start_idx, end_idx, start_ts, end_ts in zip(start_indices, end_indices, start_times, end_times):
            # Extract metrics
            metrics = extract_weight_metrics(df_raw, int(start_ts), int(end_ts), cell)

            # Assign quality mark
            quality_mark = assign_quality_mark(metrics)

            # Create result row
            row = {
                "Event_start": start_ts,
                "Event_end": end_ts,
                "Event_start_time": pd.Timestamp(start_ts, unit='ms') + pd.Timedelta(hours=2),
                "Event_end_time": pd.Timestamp(end_ts, unit='ms') + pd.Timedelta(hours=2),
                "DGT": dgt,
                "cell": cell,
                "db_name": db_path.name,
                "date": filename_date,
                "quality_mark": quality_mark,
            }

            # Add all metrics
            row.update(metrics)
            results.append(row)

    if results:
        result_df = pd.DataFrame(results)
        print(f"{len(result_df)} events")
        return result_df, analysis_date, file_start_time, file_end_time
    else:
        print("No events detected")
        return pd.DataFrame(), analysis_date, file_start_time, file_end_time


def analyze_weight_files(db_paths: List[Path], config: Optional[Dict] = None) -> Tuple[pd.DataFrame, Optional[datetime], Dict]:
    """
    Analyze multiple weight log files

    Args:
        db_paths: List of paths to .db files
        config: Optional config dict

    Returns:
        (Combined DataFrame with all events, earliest analysis_date, file_info_dict)
        file_info_dict maps db_name -> (file_start_time, file_end_time)
    """
    all_results = []
    earliest_date = None
    file_info = {}

    for db_path in db_paths:
        df, db_date, file_start, file_end = analyze_weight_file(db_path, config)
        if not df.empty:
            all_results.append(df)

        # Track earliest date
        if db_date is not None:
            if earliest_date is None or db_date < earliest_date:
                earliest_date = db_date

        # Store file time info
        file_info[db_path.name] = (file_start, file_end)

    if all_results:
        return pd.concat(all_results, ignore_index=True), earliest_date, file_info
    else:
        return pd.DataFrame(), earliest_date, file_info


if __name__ == "__main__":
    # Allow testing from command line
    if len(sys.argv) > 1:
        db_file = Path(sys.argv[1])
        if db_file.exists():
            df = analyze_weight_file(db_file)
            print("\nResults:")
            print(df.to_string())
        else:
            print(f"File not found: {db_file}")
    else:
        print("Usage: python3 nightly_check_weight_data.py <db_file>")
