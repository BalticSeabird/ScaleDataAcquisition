"""
Generate sample plots for Q2 (RECOMMENDED) and Q3 (AGGRESSIVE) quality classifications.
Creates 10 example events per station for each quality tier.
Iterates through all available databases for each station to gather enough samples.
"""

import numpy as np
import pandas as pd
import sqlite3
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))

def load_db(db_path: Path, table):
    """Load database table into dataframe"""
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f'SELECT * from {table}', con)
    except Exception as e:
        df = None
    con.close()
    return df

def apply_quality_filter(events_df, quality_tier):
    """Apply quality classification filters"""
    if quality_tier == 'Q2_RECOMMENDED':
        # RECOMMENDED Rule: balanced
        return events_df[
            (events_df['weight_median'] >= 0.7) &
            (events_df['weight_median'] <= 1.0) &
            (events_df['weight_var'] < 0.0005) &
            (events_df['tare_before_var'] < 0.0001) &
            (events_df['tare_after_var'] < 0.0001) &
            (abs(events_df['tare_before_mean'] - events_df['tare_after_mean']) < 0.01) &
            (events_df['event_duration_ms'] > 2000) &
            (events_df['event_data_points'] > 50)
        ]
    elif quality_tier == 'Q3_AGGRESSIVE':
        # AGGRESSIVE Rule: highest quality
        return events_df[
            (events_df['weight_median'] >= 0.75) &
            (events_df['weight_median'] <= 0.95) &
            (events_df['weight_var'] < 0.0001) &
            (events_df['tare_before_var'] < 0.00005) &
            (events_df['tare_after_var'] < 0.00005) &
            (abs(events_df['tare_before_mean'] - events_df['tare_after_mean']) < 0.005) &
            (events_df['event_duration_ms'] > 10000) &
            (events_df['event_data_points'] > 200) &
            (events_df['signal_cv_percent'] < 2.0)
        ]
    return pd.DataFrame()

def create_event_plots(events_df, quality_tier, station, num_plots=10):
    """Create plots for quality classification events for a specific station"""

    # Get events for this station, sorted for consistency
    station_events = events_df[events_df['Cameraname'] == station].sort_values('Event_start')
    if len(station_events) == 0:
        return 0

    plot_count = 0
    processed_dbs = {}
    events_to_process = station_events.head(num_plots * 3)  # Get more to account for failures

    for idx, (row_idx, event) in enumerate(events_to_process.iterrows()):
        if plot_count >= num_plots:
            break

        db_name = event['db_name']

        # Find the database file
        db_files = list(Path('../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(db_name))
        if not db_files:
            continue

        db_file = db_files[0]

        # Load cell data if we haven't loaded this database yet
        if db_name not in processed_dbs:
            data = load_db(db_file, "cells")
            if data is None:
                continue
            processed_dbs[db_name] = data
        else:
            data = processed_dbs[db_name]

        start = event["Event_start"]
        end = event["Event_end"]
        cell = int(event["cell"])
        cell_col = f"cell_{cell}"

        # Extract full time window
        full_start = start - 2500 - 1000
        full_end = end + 2500 + 1000

        mask = (data["timestamp"] >= full_start) & (data["timestamp"] <= full_end)
        signal_data = data[mask].copy()

        if len(signal_data) == 0:
            continue

        # Create times relative to event start
        signal_data["time_offset"] = (signal_data["timestamp"] - start) / 1000
        weight = signal_data[cell_col].values
        time_offset = signal_data["time_offset"].values

        weight_value = event["weight_median"]
        duration = event["event_duration_ms"]

        # Create figure with full view
        fig, ax = plt.subplots(1, 1, figsize=(14, 6))

        ax.plot(time_offset, weight, 'b-', linewidth=1.5, label='Raw Weight Signal')

        # Mark regions
        ax.axvspan(-2.5, -0.75, alpha=0.15, color='green', label='Tare Before')
        ax.axvspan(1, (end-start-1000)/1000, alpha=0.15, color='red', label='Event Window')
        ax.axvspan((end-start)/1000 + 0.75, (end-start)/1000 + 3.25, alpha=0.15, color='orange', label='Tare After')

        ax.axvline(0, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Event Start')
        ax.axvline((end-start)/1000, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Event End')

        ax.set_xlabel('Time offset from event start (seconds)', fontsize=11)
        ax.set_ylabel('Weight (kg)', fontsize=11)
        ax.set_title(f'{station} - {quality_tier} - Event {plot_count+1}: Weight={weight_value:.3f}kg, Duration={duration/1000:.1f}s',
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=10)

        plt.tight_layout()

        # Save figure
        output_dir = Path("out/quality_classifications_v2")
        output_dir.mkdir(exist_ok=True)

        clean_station = station.replace('/', '_')
        fig.savefig(output_dir / f"{quality_tier}_{clean_station}_event{plot_count+1:02d}.png",
                   dpi=100, bbox_inches='tight')

        plt.close(fig)
        plot_count += 1

    return plot_count

# Load events database
print("Loading events database...")
events_db = load_db(Path("out/Events23-25_weights.db"), "event")
print(f"Total events: {len(events_db)}\n")

# Get unique stations
stations = events_db['Cameraname'].unique()
print(f"Found {len(stations)} unique stations\n")

# Process each quality tier
quality_tiers = ['Q2_RECOMMENDED', 'Q3_AGGRESSIVE']

for quality_tier in quality_tiers:
    print(f"\n{'='*60}")
    print(f"Processing {quality_tier}")
    print(f"{'='*60}\n")

    filtered_events = apply_quality_filter(events_db, quality_tier)
    print(f"Total: {len(filtered_events)} events matching {quality_tier}\n")

    filtered_stations = sorted(filtered_events['Cameraname'].unique())
    total_plots = 0

    for station in filtered_stations:
        station_events = filtered_events[filtered_events['Cameraname'] == station]
        print(f"  {station}: {len(station_events)} total events", end=" ... ")

        plots = create_event_plots(filtered_events, quality_tier, station, num_plots=10)
        total_plots += plots
        print(f"created {plots} plots")

    print(f"\n✓ Generated {total_plots} plots for {quality_tier}")

print(f"\n{'='*60}")
print("✓ All plots saved to: out/quality_classifications_v2/")
print("Ready for visual inspection!")
