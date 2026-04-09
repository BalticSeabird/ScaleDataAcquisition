"""
Generate boundary analysis plots for Q2 (RECOMMENDED) and Q3 (LENIENT) quality classifications.
Inspects actual event data to visually validate these rules are good enough in practice.
"""

import numpy as np
import pandas as pd
import sqlite3
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))
from functions import create_connection

def load_db(db_path: Path, table):
    """Load database table into dataframe"""
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f'SELECT * from {table}', con)
    except:
        df = None
        print(f'Error loading {db_path.name}')
    con.close()
    return df

# ============================================================================
# QUALITY CLASSIFICATION RULES (from MEMORY.md)
# ============================================================================

# Parameters for tare/event windows (same as current step2 logic)
tare_length = 2500           # ms
start_delay = 1000           # ms
end_delay = 1000             # ms
tare_offset_before = 750     # ms
tare_offset_after = 750      # ms

# Load events database
events_db = load_db(Path("out/Events23-25_weights.db"), "event")
print(f"Total events: {len(events_db)}")

# Q2: RECOMMENDED Rule (using pre-calculated quality flags)
q2_events = events_db[events_db['passes_moderate'] == True].copy()
print(f"Q2 (RECOMMENDED) events: {len(q2_events)}")

# Q3: LENIENT Rule (using pre-calculated quality flags)
q3_events = events_db[events_db['passes_lenient'] == True].copy()
print(f"Q3 (LENIENT) events: {len(q3_events)}")

# Extract year from db_name
q2_events["year"] = q2_events["db_name"].str[:4].astype(int)
q3_events["year"] = q3_events["db_name"].str[:4].astype(int)

# Get unique stations
stations_q2 = q2_events['Cameraname'].unique()
stations_q3 = q3_events['Cameraname'].unique()
all_stations = sorted(set(stations_q2) | set(stations_q3))

print(f"\nStations in Q2: {len(stations_q2)}")
print(f"Stations in Q3: {len(stations_q3)}")
print(f"Total unique stations: {len(all_stations)}")
print(f"Stations: {all_stations}\n")

# Create output directory
output_dir = Path("out/quality_boundary_analysis")
output_dir.mkdir(exist_ok=True)

# ============================================================================
# GENERATE PLOTS
# ============================================================================

fig_counter = 0
quality_counts = {"Q2": 0, "Q3": 0}

for quality, events_subset, quality_label in [
    ("Q2", q2_events, "RECOMMENDED"),
    ("Q3", q3_events, "LENIENT")
]:
    print(f"\n{'=' * 70}")
    print(f"Processing {quality} ({quality_label}) events")
    print(f"{'=' * 70}\n")

    # Get events per station
    events_by_station = events_subset.groupby('Cameraname')

    for station in sorted(events_by_station.groups.keys()):
        station_events = events_by_station.get_group(station)
        print(f"{station}: {len(station_events)} events, sampling 10...")

        # Sample up to 10 events from this station
        sample_events = station_events.sample(n=min(10, len(station_events)), random_state=42)

        for sample_idx, (row_idx, event) in enumerate(sample_events.iterrows()):
            db_name = event["db_name"]
            db_file = list(Path('../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(db_name))

            if not db_file:
                print(f"  Database not found: {db_name}")
                continue

            # Load cell data
            data = load_db(db_file[0], "cells")
            if data is None:
                continue

            start = event["Event_start"]
            end = event["Event_end"]
            cell = event["cell"]
            cell_col = f"cell_{cell}"

            # Extract full time window
            full_start = start - tare_length - 1000
            full_end = end + tare_length + 1000

            mask = (data["timestamp"] >= full_start) & (data["timestamp"] <= full_end)
            signal_data = data[mask].copy()

            if len(signal_data) == 0:
                continue

            # Create times relative to event start
            signal_data["time_offset"] = (signal_data["timestamp"] - start) / 1000
            weight = signal_data[cell_col].values
            time_offset = signal_data["time_offset"].values

            # Get event metadata
            camera = event["Cameraname"]
            weight_value = event["weight_median"]
            duration = event["event_duration_ms"]
            weight_var = event["weight_var"]

            # ================================================================
            # FIGURE 1: Full view
            # ================================================================
            fig, ax1 = plt.subplots(figsize=(14, 5))

            ax1.plot(time_offset, weight, 'b-', linewidth=1.5, label='Raw Weight Signal')

            # Mark regions
            ax1.axvspan(-tare_length/1000, -tare_offset_before/1000, alpha=0.2, color='green', label='Tare Before')
            ax1.axvspan(start_delay/1000, (end-start-start_delay)/1000, alpha=0.2, color='red', label='Event Window')
            ax1.axvspan((end-start)/1000 + tare_offset_after/1000, (end-start)/1000 + tare_offset_after/1000 + tare_length/1000, alpha=0.2, color='orange', label='Tare After')

            # Mark exact boundaries
            ax1.axvline(0, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Event Start')
            ax1.axvline((end-start)/1000, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Event End')

            ax1.set_xlabel('Time offset from event start (seconds)')
            ax1.set_ylabel('Weight (kg)')
            ax1.set_title(f'{quality} - {camera}: Weight={weight_value:.3f}kg, Duration={duration/1000:.1f}s, Var={weight_var:.6f}')
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='upper right', fontsize=9)

            plt.tight_layout()
            fig.savefig(output_dir / f"{quality}_full_{fig_counter:03d}_{camera}.png", dpi=100, bbox_inches='tight')
            plt.close(fig)

            # ================================================================
            # FIGURE 2: Start and end boundary zooms
            # ================================================================
            fig, (ax3, ax4) = plt.subplots(1, 2, figsize=(14, 5))

            # Start boundary zoom
            start_zoom_begin = -3
            start_zoom_end = 2
            mask_start = (time_offset >= start_zoom_begin) & (time_offset <= start_zoom_end)
            ax3.plot(time_offset[mask_start], weight[mask_start], 'b-', linewidth=2, marker='o', markersize=4, label='Raw Signal')

            ax3.axvspan(-tare_length/1000, -tare_offset_before/1000, alpha=0.15, color='green', label='Tare Before')
            ax3.axvspan(start_delay/1000, 0.5, alpha=0.15, color='red', label='Event Window Start')
            ax3.axvline(0, color='black', linestyle='--', linewidth=2, label='Event Start (0s)')
            ax3.axvline(start_delay/1000, color='red', linestyle=':', linewidth=2, alpha=0.7, label=f'Actual Event Start (+{start_delay}ms)')

            ax3.set_xlabel('Time offset from event start (seconds)')
            ax3.set_ylabel('Weight (kg)')
            ax3.set_title(f'{quality} - START BOUNDARY\n{camera}')
            ax3.grid(True, alpha=0.3)
            ax3.legend(fontsize=8)

            # End boundary zoom
            event_duration_sec = (end - start) / 1000
            end_zoom_begin = event_duration_sec - 2
            end_zoom_end = event_duration_sec + 3
            mask_end = (time_offset >= end_zoom_begin) & (time_offset <= end_zoom_end)
            ax4.plot(time_offset[mask_end], weight[mask_end], 'b-', linewidth=2, marker='o', markersize=4, label='Raw Signal')

            ax4.axvspan(end_zoom_begin, event_duration_sec - end_delay/1000, alpha=0.15, color='red', label='Event Window End')
            ax4.axvspan(event_duration_sec + tare_offset_after/1000, event_duration_sec + tare_offset_after/1000 + tare_length/1000, alpha=0.15, color='orange', label='Tare After')
            ax4.axvline(event_duration_sec, color='black', linestyle='--', linewidth=2, label=f'Event End ({event_duration_sec:.1f}s)')
            ax4.axvline(event_duration_sec - end_delay/1000, color='red', linestyle=':', linewidth=2, alpha=0.7, label=f'Actual Event End (-{end_delay}ms)')

            ax4.set_xlabel('Time offset from event start (seconds)')
            ax4.set_ylabel('Weight (kg)')
            ax4.set_title(f'{quality} - END BOUNDARY\n{camera}')
            ax4.grid(True, alpha=0.3)
            ax4.legend(fontsize=8)

            plt.tight_layout()
            fig.savefig(output_dir / f"{quality}_boundaries_{fig_counter:03d}_{camera}.png", dpi=100, bbox_inches='tight')
            plt.close(fig)

            fig_counter += 1
            quality_counts[quality] += 1

print(f"\n{'=' * 70}")
print(f"Summary:")
print(f"  Q2 (RECOMMENDED) plots generated: {quality_counts['Q2']}")
print(f"  Q3 (LENIENT) plots generated: {quality_counts['Q3']}")
print(f"  Total plots: {fig_counter * 2}")  # 2 plots per event
print(f"  Saved to: {output_dir}")
print(f"{'=' * 70}")
