"""
Generate diagnostic plots for event classification across all stations.
Similar to VALIDATED_ANALYSIS.md analysis but extended to all cameras.

Creates 50 example plots per event category (good/bad/missing) per camera.
"""

import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
import sys
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from functions import create_connection

warnings.filterwarnings('ignore')

# Configuration
TARE_LENGTH = 10000  # ms
START_DELAY = 2000   # ms
PLOTS_PER_CATEGORY = 50
OUTPUT_BASE_DIR = Path("out/diagnostic_plots")

# Event categorization thresholds (to be refined based on visual inspection)
GOOD_WEIGHT_MIN = 0.76
GOOD_WEIGHT_MAX = 1.11
BAD_WEIGHT_MAX = 0.40
UNSTABLE_WEIGHT_MAX = 1.30

def load_db(db_path: Path, table):
    """Load database and convert to DataFrame"""
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f'SELECT * from {table}', con)
    except Exception as e:
        df = None
        print(f'SQL read error for {db_path.name}: {e}')
    con.close()
    return df


def categorize_event(row):
    """
    Categorize event based on weight and signal quality metrics.
    Returns: 'good', 'bad', or 'missing'
    """
    weight = row['weight_median']
    duration = row['event_duration_ms']
    cv = row['signal_cv_percent']
    data_points = row['event_data_points']

    # Missing events
    if pd.isna(weight):
        return 'missing'

    # Good events: stable weight, stable signal, sufficient duration
    if (GOOD_WEIGHT_MIN <= weight <= GOOD_WEIGHT_MAX and
        duration >= 2000 and
        data_points >= 10 and
        (pd.isna(cv) or cv < 15)):
        return 'good'

    # Bad events: low weight, high variability, or problematic
    if (weight < BAD_WEIGHT_MAX or
        weight > UNSTABLE_WEIGHT_MAX or
        (not pd.isna(cv) and cv > 25) or
        (duration > 0 and duration < 500)):
        return 'bad'

    # Intermediate (neither clearly good nor bad)
    return 'intermediate'


def get_raw_data(db_file: Path, table_name: str = "cells"):
    """Load raw sensor data from weight log database"""
    try:
        con = sqlite3.connect(db_file)
        df = pd.read_sql_query(f'SELECT * from {table_name}', con)
        con.close()
        return df
    except:
        return None


def plot_event(ax, data, start_ms, end_ms, cell, title, stats_text):
    """Plot single event with tare windows and event window"""

    # Extract data windows
    tare_before_start = start_ms - TARE_LENGTH
    tare_after_end = end_ms + TARE_LENGTH
    event_display_start = start_ms - TARE_LENGTH * 1.2
    event_display_end = end_ms + TARE_LENGTH * 1.2

    # Filter to display window
    col_name = f"cell_{cell}"
    display_data = data[
        (data['timestamp'] >= event_display_start) &
        (data['timestamp'] <= event_display_end)
    ].copy()

    if len(display_data) == 0:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                transform=ax.transAxes, fontsize=10, color='red')
        ax.set_title(title, fontsize=10, fontweight='bold')
        return

    # Plot full window (background)
    ax.plot(display_data['timestamp'], display_data[col_name],
            color='lightgray', linewidth=1, label='Raw signal', alpha=0.7)

    # Highlight different regions
    # Tare before (blue)
    tare_before = display_data[
        (display_data['timestamp'] > tare_before_start) &
        (display_data['timestamp'] <= start_ms)
    ]
    if len(tare_before) > 0:
        ax.plot(tare_before['timestamp'], tare_before[col_name],
                color='blue', linewidth=1.5, label='Tare before', alpha=0.8)

    # Event window (red)
    event_data = display_data[
        (display_data['timestamp'] > start_ms + START_DELAY) &
        (display_data['timestamp'] < end_ms - START_DELAY)
    ]
    if len(event_data) > 0:
        ax.plot(event_data['timestamp'], event_data[col_name],
                color='red', linewidth=2, label='Event (used)', alpha=0.9)
    elif len(event_data) == 0:
        # Show event window even if missing data (x marks the spot)
        ax.axvspan(start_ms + START_DELAY, end_ms - START_DELAY,
                   alpha=0.1, color='red', label='Event (no data)')

    # Tare after (green)
    tare_after = display_data[
        (display_data['timestamp'] >= end_ms) &
        (display_data['timestamp'] < tare_after_end)
    ]
    if len(tare_after) > 0:
        ax.plot(tare_after['timestamp'], tare_after[col_name],
                color='green', linewidth=1.5, label='Tare after', alpha=0.8)

    # Vertical lines for event boundaries
    ax.axvline(start_ms, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(end_ms, color='red', linestyle='--', alpha=0.5, linewidth=1)

    # Labels and formatting
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.set_xlabel('Time (ms)', fontsize=8)
    ax.set_ylabel('Weight (kg)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.3)

    # Add statistics text box
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=7, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8, pad=0.3),
            family='monospace')


def generate_plots_for_station(events_df, all_events_db, station_name, raw_data_cache):
    """Generate diagnostic plots for a single station"""

    print(f"\n{'='*80}")
    print(f"Processing station: {station_name}")
    print(f"{'='*80}")

    station_events = all_events_db[all_events_db['Cameraname'] == station_name].copy()

    if len(station_events) == 0:
        print(f"No events found for {station_name}")
        return

    # Categorize all events
    station_events['category'] = station_events.apply(categorize_event, axis=1)

    # Print statistics
    print(f"Total events: {len(station_events)}")
    for cat in ['good', 'bad', 'missing', 'intermediate']:
        count = (station_events['category'] == cat).sum()
        pct = 100 * count / len(station_events)
        print(f"  {cat:12s}: {count:5d} ({pct:5.1f}%)")

    # Create output directory structure
    station_dir = OUTPUT_BASE_DIR / station_name

    # Generate plots for each category
    for category in ['good', 'bad', 'missing']:
        cat_events = station_events[station_events['category'] == category].copy()

        if len(cat_events) == 0:
            print(f"  No {category} events found")
            continue

        # Sample up to PLOTS_PER_CATEGORY events
        sample_size = min(PLOTS_PER_CATEGORY, len(cat_events))
        sampled_events = cat_events.sample(n=sample_size, random_state=42)

        print(f"  Generating {sample_size} plots for {category} events...")

        # Create output directory for this category
        category_dir = station_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Generate plots
        for idx, (_, event_row) in enumerate(sampled_events.iterrows(), 1):
            try:
                # Get raw data for this database file
                db_name = event_row['db_name']

                if db_name not in raw_data_cache:
                    db_file = list(Path(f'../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(db_name))
                    if not db_file:
                        continue
                    raw_data = get_raw_data(db_file[0])
                    if raw_data is not None:
                        raw_data_cache[db_name] = raw_data
                    else:
                        continue
                else:
                    raw_data = raw_data_cache[db_name]

                # Extract event info
                cell = int(event_row['cell'])
                start_ms = event_row['Event_start']
                end_ms = event_row['Event_end']
                weight = event_row['weight_median']
                duration = event_row['event_duration_ms']
                cv = event_row['signal_cv_percent']
                data_points = event_row['event_data_points']
                tare_before_m = event_row['tare_before_mean']
                tare_after_m = event_row['tare_after_mean']

                # Create figure
                fig, ax = plt.subplots(figsize=(10, 4))

                # Build stats text
                stats_text = (
                    f"Weight: {weight:.3f} kg\n"
                    f"Duration: {duration:.0f} ms\n"
                    f"Data points: {data_points:.0f}\n"
                    f"CV: {cv:.1f}%\n"
                    f"Tare before: {tare_before_m:.4f}\n"
                    f"Tare after: {tare_after_m:.4f}"
                )

                # Plot event
                plot_event(ax, raw_data, start_ms, end_ms, cell,
                          f"{station_name} - {category.upper()} Event {idx}",
                          stats_text)

                # Save figure
                fig_name = category_dir / f"event_{idx:03d}.png"
                plt.tight_layout()
                plt.savefig(fig_name, dpi=100, bbox_inches='tight')
                plt.close(fig)

                if idx % 10 == 0:
                    print(f"    Generated {idx}/{sample_size} plots")

            except Exception as e:
                print(f"    Error plotting event {idx}: {e}")
                plt.close('all')
                continue

        print(f"  ✓ Saved {sample_size} {category} plots to {category_dir}")


def main():
    print("DIAGNOSTIC PLOT GENERATION")
    print("Generating event classification plots for all stations\n")

    # Load event database with new statistics
    print("Loading event database...")
    con = sqlite3.connect("out/Events23-25_weights.db")
    all_events = pd.read_sql_query('SELECT * from event', con)
    con.close()

    print(f"Loaded {len(all_events)} total events across {all_events['Cameraname'].nunique()} stations\n")

    # Get unique stations
    stations = sorted(all_events['Cameraname'].unique())

    # Cache for raw data to avoid reloading
    raw_data_cache = {}

    # Generate plots for each station
    for station_name in stations:
        generate_plots_for_station(all_events, all_events, station_name, raw_data_cache)

    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Diagnostic plots saved to: {OUTPUT_BASE_DIR}")
    print(f"\nDirectory structure:")
    print(f"  {OUTPUT_BASE_DIR}/")
    for station_name in stations:
        print(f"    {station_name}/")
        print(f"      good/")
        print(f"      bad/")
        print(f"      missing/")
    print(f"\nPlease manually inspect the plots to refine classification rules.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
