

import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys
import os
from datetime import datetime
import matplotlib.pyplot as plt
import warnings
import json

# Add utils to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from functions import create_connection



# Now
# Assign scale name to each event 
# Name each event
# Get weight data for each event 

def load_db(db_path: Path, table):           #load database and change into dataframe#
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f'SELECT * from {table}', con)
    except:
        df = [0]
        print(f'sql read error for {db_path.name}')
    con.close()
    return df


# Load and display debug report from step1
print("\n" + "="*80)
print("LOADING DEBUG REPORT FROM STEP 1")
print("="*80 + "\n")

debug_report_path = Path("state_machine_debug.json")
if debug_report_path.exists():
    with open(debug_report_path, "r") as f:
        debug_report = json.load(f)

    summary = debug_report["summary"]
    print(f"Step 1 Execution Report:")
    print(f"  Start time: {debug_report['start_time']}")
    print(f"  End time: {debug_report['end_time']}")
    print(f"  Files processed: {summary['total_files_processed']}")
    print(f"  Cells processed: {summary['total_cells_processed']} (expected: {summary['expected_cells']})")
    print(f"  Total events: {summary['total_events_written']}")
    print(f"  Avg events/cell: {summary['average_events_per_cell']}")

    if summary['cell_count_mismatch']:
        print(f"  ⚠️  WARNING: Cell count mismatch detected!")
    else:
        print(f"  ✓ Cell count verified")
    print()
else:
    print("⚠️  WARNING: state_machine_debug.json not found. Step 1 may not have completed.")
    debug_report = None
    print()


# Delete old version if existing
if os.path.exists("out/Events23-25_weights.db"):
    os.remove("out/Events23-25_weights.db")


# Create empty db
con_local = create_connection("out/Events23-25_weights.db")

# File with events 
events = load_db("out/Events23-25.db", "event")

# Scale names
with open("./config/ScaleSystemNames.json", "r") as f:
    lookup_data = json.load(f)
lookup = pd.DataFrame(lookup_data["scale_system_mappings"])
lookup["startdate"] = pd.to_datetime(lookup["startdate"])
lookup["enddate"] = pd.to_datetime(lookup["enddate"])
# Rename columns to match expected format from original CSV
lookup.rename(columns={
    "dgt": "DGT",
    "cell": "cell",
    "startdate": "Startdate",
    "enddate": "Enddate",
    "scalename": "Scalename",
    "cameraname": "Cameraname",
    "comment": "Comment"
}, inplace=True)



# List of databases to read raw weights from
dbs = events["db_name"].unique()

# Params for weight events
# These match analyze_tare_window_boundaries.py for consistency
tare_length = 2500              # ms - duration of tare window before/after event
tare_offset_before = 750        # ms - gap between event_start and tare_before end (bird stepping on)
tare_offset_after = 750         # ms - gap between event_end and tare_after start (bird stepping off)
start_delay = 1000              # ms - signal to skip at START of event (ramp-up)
end_delay = 1000                # ms - signal to skip at END of event (ramp-down)


for db in dbs:        
    event_info = events[events["db_name"] == db].copy()
    dgt = event_info.iloc[0]["DGT"]
    date = event_info.iloc[0]["Event_start_time"]
    db_file = list(Path(f'../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(db))
    print(db_file[0])
    print(db)
    data = load_db(db_file[0], "cells")

    # Get weight data for each event
    weight_median = []
    weight_var = []
    tare_before_mean_list = []
    tare_before_var_list = []
    tare_after_mean_list = []
    tare_after_var_list = []
    event_duration_ms_list = []
    event_data_point_count = []
    tare_before_point_count = []
    tare_after_point_count = []
    event_min_list = []
    event_max_list = []
    event_range_list = []
    event_cv_list = []  # Coefficient of variation

    for row in event_info.index:
        start = event_info["Event_start"].loc[row]
        end = event_info["Event_end"].loc[row]
        cell = event_info["cell"].loc[row]

        # Extract time windows with offsets
        # Event window: from start + start_delay to end - end_delay
        cond1 = data["timestamp"] > start + start_delay
        cond2 = data["timestamp"] < end - end_delay

        # Tare before: from start - tare_length to start - tare_offset_before
        cond3 = data["timestamp"] >= start - tare_length
        cond4 = data["timestamp"] < start - tare_offset_before

        # Tare after: from end + tare_offset_after to end + tare_offset_after + tare_length
        cond5 = data["timestamp"] >= end + tare_offset_after
        cond6 = data["timestamp"] < end + tare_offset_after + tare_length

        data_event = data[cond1 & cond2][f"cell_{cell}"]
        data_before = data[cond3 & cond4][f"cell_{cell}"]
        data_after = data[cond5 & cond6][f"cell_{cell}"]

        # Calculate event duration
        event_duration_ms = end - start
        event_duration_ms_list.append(event_duration_ms)

        # Count data points
        event_data_point_count.append(len(data_event))
        tare_before_point_count.append(len(data_before))
        tare_after_point_count.append(len(data_after))

        # Calculate tare statistics
        tare_before_mean_list.append(data_before.mean() if len(data_before) > 0 else np.nan)
        tare_before_var_list.append(data_before.var() if len(data_before) > 0 else np.nan)
        tare_after_mean_list.append(data_after.mean() if len(data_after) > 0 else np.nan)
        tare_after_var_list.append(data_after.var() if len(data_after) > 0 else np.nan)

        if len(data_event) > 5:
            weight_med = data_event.median()
            weight_var.append(data_event.var())

            # Calculate signal statistics
            event_min_list.append(data_event.min())
            event_max_list.append(data_event.max())
            event_range = data_event.max() - data_event.min()
            event_range_list.append(event_range)

            # Coefficient of variation (std / mean) - measure of stability
            event_std = data_event.std()
            event_mean = data_event.mean()
            if event_mean != 0:
                cv = (event_std / abs(event_mean)) * 100  # as percentage
                event_cv_list.append(cv)
            else:
                event_cv_list.append(np.nan)

            tare_before_median = data_before.median()
            tare_after_median = data_after.median()
            tare_average = (tare_before_median + tare_after_median)/2
            weight_median.append(weight_med - tare_average)
        else:
            weight_var.append(np.nan)
            weight_median.append(np.nan)
            event_min_list.append(np.nan)
            event_max_list.append(np.nan)
            event_range_list.append(np.nan)
            event_cv_list.append(np.nan)

        # Add columns for weight data
    event_info["weight_median"] = weight_median
    event_info["weight_var"] = weight_var
    event_info["tare_before_mean"] = tare_before_mean_list
    event_info["tare_before_var"] = tare_before_var_list
    event_info["tare_after_mean"] = tare_after_mean_list
    event_info["tare_after_var"] = tare_after_var_list
    event_info["event_duration_ms"] = event_duration_ms_list
    event_info["event_data_points"] = event_data_point_count
    event_info["tare_before_points"] = tare_before_point_count
    event_info["tare_after_points"] = tare_after_point_count
    event_info["event_min"] = event_min_list
    event_info["event_max"] = event_max_list
    event_info["event_range"] = event_range_list
    event_info["signal_cv_percent"] = event_cv_list  # Coefficient of variation as %
    
    # Time and date info, frame numbers, etc. 
    event_info["Event_start_time"] = pd.to_datetime(event_info["Event_start"]*1000*1000)+pd.Timedelta(hours = 2)
    event_info["Event_end_time"] = pd.to_datetime(event_info["Event_end"]*1000*1000)+pd.Timedelta(hours = 2)
    event_info["Day"] = event_info["Event_start_time"].dt.date
    event_info["Hour"] = event_info["Event_start_time"].dt.hour
    Video_start = [pd.to_datetime(format(event_info["Event_start_time"].loc[row], f"%Y-%m-%d %H:00:00")) for row in event_info.index]
    event_info["Video_start"] = Video_start
    event_info["Sec_start"] = (event_info["Event_start_time"]-event_info["Video_start"])/np.timedelta64(1,'s')
    event_info["Sec_end"] = (event_info["Event_end_time"]-event_info["Video_start"])/np.timedelta64(1,'s')
    event_info["Frame_start"] = event_info["Sec_start"]*25
    event_info["Frame_end"] = event_info["Sec_end"]*25        
    Video_timestring = [format(event_info["Event_start_time"].loc[row], f"%Y-%m-%d_%H.00.00.mp4") for row in event_info.index]
    event_info["Video_timestring"] = Video_timestring

    # Link to scale name
    interval = []
    for row in lookup.index:
        start = lookup["Startdate"][row]
        end = lookup["Enddate"][row]+pd.Timedelta(days = 1)
        interval.append(pd.Interval(start, end, closed = "neither"))

    lookup["Interval"] = interval

    # Pick out matching dates (only first row of data) 
    inside = []
    for row in lookup.index: 
        if pd.to_datetime(date) in lookup["Interval"][row]:
            inside.append(1)
        else: 
            inside.append(0) 

    lookup["Inside"] = inside
    cond1 = lookup["Inside"] == 1
    cond2 = lookup["DGT"] == dgt
    lookup_reduced = lookup[cond1 & cond2]
    lookup_reduced = lookup_reduced.sort_values(["cell"])
    names = lookup_reduced["Cameraname"]

    event_info = event_info.merge(lookup_reduced[["DGT", "cell", "Cameraname"]], on = ["DGT", "cell"], how = "inner")

    # Path for full video
    Video_path = ["Auklab1_"+event_info["Cameraname"].loc[row]+"_"+event_info["Video_timestring"].loc[row] for row in event_info.index]
    event_info["Video_path"] = Video_path

    # Event ID
    event_info["Event_ID"] = [event_info["Cameraname"].loc[row]+"_"+str(event_info["Day"].loc[row])+"_"+str(event_info["Hour"].loc[row])+"_"+str(event_info.index[row]).zfill(2) for row in event_info.index]

    event_info.to_sql("event", con_local, if_exists='append')
        



# ============================================================================
# Print comprehensive summary statistics for quality assurance
# ============================================================================
print("\n" + "="*80)
print("DATA QUALITY SUMMARY STATISTICS")
print("="*80 + "\n")

# Load final database to get all accumulated events
con_final = sqlite3.connect("out/Events23-25_weights.db")
all_events = pd.read_sql_query('SELECT * from event', con_final)
con_final.close()

print(f"Total events in database: {len(all_events)}")
print(f"Total scales/stations: {all_events['Cameraname'].nunique()}")
print()

# Weight statistics
print("WEIGHT STATISTICS:")
print(f"  Valid weights (not NaN): {all_events['weight_median'].notna().sum()}")
print(f"  Missing weights (NaN): {all_events['weight_median'].isna().sum()}")
print(f"  Weight range: {all_events['weight_median'].min():.3f} - {all_events['weight_median'].max():.3f} kg")
print(f"  Weight mean: {all_events['weight_median'].mean():.3f} ± {all_events['weight_median'].std():.3f} kg")
print(f"  Weight median: {all_events['weight_median'].median():.3f} kg")
print()

# Weight distribution analysis
print("WEIGHT CLASSIFICATION (Quality Check):")
good_weights = all_events[(all_events['weight_median'] >= 0.76) & (all_events['weight_median'] <= 1.11)]
low_weights = all_events[(all_events['weight_median'] > 0) & (all_events['weight_median'] < 0.4)]
high_weights = all_events[all_events['weight_median'] > 1.15]
missing_weights = all_events[all_events['weight_median'].isna()]

print(f"  Good/Normal (0.76-1.11 kg): {len(good_weights)} ({100*len(good_weights)/len(all_events):.1f}%)")
print(f"  Low (<0.4 kg, likely noise): {len(low_weights)} ({100*len(low_weights)/len(all_events):.1f}%)")
print(f"  High (>1.15 kg, likely stacked): {len(high_weights)} ({100*len(high_weights)/len(all_events):.1f}%)")
print(f"  Missing/NaN: {len(missing_weights)} ({100*len(missing_weights)/len(all_events):.1f}%)")
print()

# Event duration analysis
print("EVENT DURATION STATISTICS:")
print(f"  Duration range: {all_events['event_duration_ms'].min():.0f} - {all_events['event_duration_ms'].max():.0f} ms")
print(f"  Duration mean: {all_events['event_duration_ms'].mean():.0f} ± {all_events['event_duration_ms'].std():.0f} ms")
print(f"  Duration median: {all_events['event_duration_ms'].median():.0f} ms")
short_events = all_events[all_events['event_duration_ms'] < 2000]
print(f"  Short events (<2000ms): {len(short_events)} ({100*len(short_events)/len(all_events):.1f}%)")
print()

# Tare statistics
print("TARE BASELINE STATISTICS (Signal Quality):")
print(f"  Tare before - mean: {all_events['tare_before_mean'].mean():.4f} ± {all_events['tare_before_mean'].std():.4f} kg")
print(f"  Tare before - variance: {all_events['tare_before_var'].mean():.6f} ± {all_events['tare_before_var'].std():.6f}")
print(f"  Tare after - mean: {all_events['tare_after_mean'].mean():.4f} ± {all_events['tare_after_mean'].std():.4f} kg")
print(f"  Tare after - variance: {all_events['tare_after_var'].mean():.6f} ± {all_events['tare_after_var'].std():.6f}")
tare_shift = abs(all_events['tare_before_mean'] - all_events['tare_after_mean'])
print(f"  Tare shift (|before - after|): {tare_shift.mean():.4f} ± {tare_shift.std():.4f} kg")
print()

# Data point coverage
print("DATA POINT COVERAGE:")
print(f"  Event data points - mean: {all_events['event_data_points'].mean():.1f} ± {all_events['event_data_points'].std():.1f}")
print(f"  Event data points - min: {all_events['event_data_points'].min():.0f}")
print(f"  Tare before points - mean: {all_events['tare_before_points'].mean():.1f} ± {all_events['tare_before_points'].std():.1f}")
print(f"  Tare after points - mean: {all_events['tare_after_points'].mean():.1f} ± {all_events['tare_after_points'].std():.1f}")
print()

# Signal stability (Coefficient of Variation)
print("SIGNAL STABILITY (Coefficient of Variation %):")
valid_cv = all_events['signal_cv_percent'].dropna()
print(f"  Mean CV: {valid_cv.mean():.1f}% (lower is more stable)")
print(f"  Median CV: {valid_cv.median():.1f}%")
print(f"  Range: {valid_cv.min():.1f}% - {valid_cv.max():.1f}%")
stable_signals = all_events[all_events['signal_cv_percent'] < 5.0]
print(f"  Highly stable (<5% CV): {len(stable_signals)} ({100*len(stable_signals)/len(all_events[all_events['signal_cv_percent'].notna()]):.1f}%)")
print()

# Event min/max range
print("EVENT SIGNAL RANGE:")
print(f"  Min value - mean: {all_events['event_min'].mean():.3f} ± {all_events['event_min'].std():.3f} kg")
print(f"  Max value - mean: {all_events['event_max'].mean():.3f} ± {all_events['event_max'].std():.3f} kg")
print(f"  Range (max-min) - mean: {all_events['event_range'].mean():.3f} ± {all_events['event_range'].std():.3f} kg")
print()

print("="*80)
print()


# Make lineplot of weight data in data_before, data_event and data_after
# Save plot to file with event name

fig, ax = plt.subplots()
y = pd.concat([data_before, data_after])
ax.plot(y.index, y)
#ax.vlines(data_event.index[0], ymin = 0, ymax = 1, color = "red")
#ax.vlines(data_event.index[-1], ymin = 0, ymax = 1, color = "red")
plt.savefig(f"out/figs/Event_example.png")