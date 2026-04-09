"""
Analyze tare and event window boundaries to optimize parameter selection.
Shows raw signals at transition points for good events.
"""

import numpy as np
import pandas as pd
import sqlite3
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
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
# PARAMETERS FOR EXPERIMENTATION
# ============================================================================
# These define the signal windows for tare baseline and event weight calculation
# Adjust these values to find the optimal balance

tare_length = 2500           # ms - duration of tare window before/after event
start_delay = 1000           # ms - signal to skip at START of event (ramp-up)
end_delay = 1000             # ms - signal to skip at END of event (ramp-down)

tare_offset_before = 750     # ms - gap between event_start and tare_before end (bird stepping on)
tare_offset_after = 750      # ms - gap between event_end and tare_after start (bird stepping off)

# Load events database
events_db = load_db(Path("out/Events23-25_weights.db"), "event")
print(f"Total events: {len(events_db)}")

# Filter for good events (based on weight range from VALIDATED_ANALYSIS)
good_events = events_db[
    (events_db['weight_median'] >= 0.76) &
    (events_db['weight_median'] <= 1.11) &
    (events_db['event_duration_ms'] >= 5000)  # At least 5 seconds
]

print(f"Good events: {len(good_events)}")
print("\nAnalyzing boundary conditions for good events...\n")

# Sample from different stations and years for comprehensive analysis
# Extract year from db_name (format: YYYYMMDD_dgtX.db)
good_events["year"] = good_events["db_name"].str[:4].astype(int)

# Get unique combinations of (year, station)
year_station_combos = good_events.groupby(["year", "Cameraname"]).size().reset_index()
print(f"Found {len(year_station_combos)} unique (year, station) combinations\n")
print("Sampling from:")
for _, row in year_station_combos.iterrows():
    print(f"  - Year {int(row['year'])}, Station: {row['Cameraname']}")
print()

# Select one database per (year, station) combination to check
dbs_to_check = []
for _, combo in year_station_combos.iterrows():
    year = combo["year"]
    station = combo["Cameraname"]
    # Get a database for this year/station combo
    db_for_combo = good_events[
        (good_events["year"] == year) &
        (good_events["Cameraname"] == station)
    ]["db_name"].iloc[0]
    dbs_to_check.append(db_for_combo)

print(f"Processing {len(dbs_to_check)} databases across all stations and years\n")

fig_counter = 0
for db_name in dbs_to_check:
    db_file = list(Path('../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(db_name))
    if not db_file:
        print(f"Database file not found: {db_name}")
        continue

    print(f"Loading {db_name}...")
    data = load_db(db_file[0], "cells")

    # Get good events from this database
    db_events = good_events[good_events["db_name"] == db_name].head(5)

    for idx, (row_idx, event) in enumerate(db_events.iterrows()):
        start = event["Event_start"]
        end = event["Event_end"]
        cell = event["cell"]
        cell_col = f"cell_{cell}"

        # Extract full time window: tare_before start through tare_after end
        full_start = start - tare_length - 1000  # 1 second extra buffer
        full_end = end + tare_length + 1000

        mask = (data["timestamp"] >= full_start) & (data["timestamp"] <= full_end)
        signal_data = data[mask].copy()

        if len(signal_data) == 0:
            continue

        # Create times relative to event start
        signal_data["time_offset"] = (signal_data["timestamp"] - start) / 1000  # Convert to seconds
        weight = signal_data[cell_col].values
        time_offset = signal_data["time_offset"].values

        # Calculate statistics
        camera = event["Cameraname"]
        weight_value = event["weight_median"]
        duration = event["event_duration_ms"]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

        # Full view
        ax1.plot(time_offset, weight, 'b-', linewidth=1.5, label='Raw Weight Signal')

        # Mark regions with current parameters
        ax1.axvspan(-tare_length/1000, -tare_offset_before/1000, alpha=0.2, color='green', label='Tare Before (current)')
        ax1.axvspan(start_delay/1000, (end-start-start_delay)/1000, alpha=0.2, color='red', label='Event Window (current)')
        ax1.axvspan((end-start)/1000 + tare_offset_after/1000, (end-start)/1000 + tare_offset_after/1000 + tare_length/1000, alpha=0.2, color='orange', label='Tare After (current)')

        # Mark exact boundaries
        ax1.axvline(0, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Event Start')
        ax1.axvline((end-start)/1000, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Event End')

        ax1.set_xlabel('Time offset from event start (seconds)')
        ax1.set_ylabel('Weight (kg)')
        ax1.set_title(f'{camera} - Event {idx+1}: Weight={weight_value:.3f}kg, Duration={duration/1000:.1f}s\nFull view with current parameter windows')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right', fontsize=9)

        # Zoomed view around boundaries
        # Create composite view showing start and end transitions
        fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(14, 5))

        # Start boundary zoom
        start_zoom_begin = -3
        start_zoom_end = 2
        mask_start = (time_offset >= start_zoom_begin) & (time_offset <= start_zoom_end)
        ax3.plot(time_offset[mask_start], weight[mask_start], 'b-', linewidth=2, marker='o', markersize=4, label='Raw Signal')

        # Mark regions
        ax3.axvspan(-tare_length/1000, -tare_offset_before/1000, alpha=0.15, color='green', label='Tare Before')
        ax3.axvspan(start_delay/1000, 0.5, alpha=0.15, color='red', label='Event Window Start')
        ax3.axvline(0, color='black', linestyle='--', linewidth=2, label='Event Start (0s)')
        ax3.axvline(start_delay/1000, color='red', linestyle=':', linewidth=2, alpha=0.7, label=f'Actual Event Start (+{start_delay}ms)')

        ax3.set_xlabel('Time offset from event start (seconds)')
        ax3.set_ylabel('Weight (kg)')
        ax3.set_title(f'START BOUNDARY - {camera}\nZoom: -3s to +2s')
        ax3.grid(True, alpha=0.3)
        ax3.legend(fontsize=9)

        # End boundary zoom
        event_duration_sec = (end - start) / 1000
        end_zoom_begin = event_duration_sec - 2
        end_zoom_end = event_duration_sec + 3
        mask_end = (time_offset >= end_zoom_begin) & (time_offset <= end_zoom_end)
        ax4.plot(time_offset[mask_end], weight[mask_end], 'b-', linewidth=2, marker='o', markersize=4, label='Raw Signal')

        # Mark regions
        ax4.axvspan(end_zoom_begin, event_duration_sec - end_delay/1000, alpha=0.15, color='red', label='Event Window End')
        ax4.axvspan(event_duration_sec + tare_offset_after/1000, event_duration_sec + tare_offset_after/1000 + tare_length/1000, alpha=0.15, color='orange', label='Tare After')
        ax4.axvline(event_duration_sec, color='black', linestyle='--', linewidth=2, label=f'Event End ({event_duration_sec:.1f}s)')
        ax4.axvline(event_duration_sec - end_delay/1000, color='red', linestyle=':', linewidth=2, alpha=0.7, label=f'Actual Event End (-{end_delay}ms)')

        ax4.set_xlabel('Time offset from event start (seconds)')
        ax4.set_ylabel('Weight (kg)')
        ax4.set_title(f'END BOUNDARY - {camera}\nZoom: Event_Duration-2s to Event_Duration+3s')
        ax4.grid(True, alpha=0.3)
        ax4.legend(fontsize=9)

        plt.tight_layout()

        # Save figures
        output_dir = Path("out/boundary_analysis")
        output_dir.mkdir(exist_ok=True)

        fig.savefig(output_dir / f"boundary_full_{fig_counter:03d}_{camera}.png", dpi=100, bbox_inches='tight')
        fig2.savefig(output_dir / f"boundary_zoom_{fig_counter:03d}_{camera}.png", dpi=100, bbox_inches='tight')

        plt.close(fig)
        plt.close(fig2)

        fig_counter += 1

        print(f"  Event {idx+1}: {camera} - Weight={weight_value:.3f}kg, Duration={duration/1000:.1f}s")
        print(f"    Raw weight range: {weight.min():.3f} - {weight.max():.3f} kg")
        print(f"    Tare before range: {weight[(time_offset >= -tare_length/1000) & (time_offset < -tare_offset_before/1000)].min():.4f} - {weight[(time_offset >= -tare_length/1000) & (time_offset < -tare_offset_before/1000)].max():.4f} kg")
        print(f"    Event window range: {weight[(time_offset >= start_delay/1000) & (time_offset < (end-start-start_delay)/1000)].min():.3f} - {weight[(time_offset >= start_delay/1000) & (time_offset < (end-start-start_delay)/1000)].max():.3f} kg")
        tare_after_start = (end - start) / 1000 + tare_offset_after / 1000
        tare_after_end = tare_after_start + tare_length / 1000
        print(f"    Tare after range: {weight[(time_offset >= tare_after_start) & (time_offset < tare_after_end)].min():.4f} - {weight[(time_offset >= tare_after_start) & (time_offset < tare_after_end)].max():.4f} kg")
        print()

print(f"\nGenerated {fig_counter} diagnostic plots")
print("Saved to: out/boundary_analysis/")
print("\nRecommendations based on inspection:")
print("- Look at the zoomed views to see if tare windows capture bird weight")
print("- Check if too much signal is cut with current start_delay and end_delay")
print("- Note the 'weight ramp' timing at event boundaries")
