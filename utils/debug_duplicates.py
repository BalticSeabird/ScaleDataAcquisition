#!/usr/bin/env python3
"""
Debug script to trace where duplicates are created in state machine processing.
This will help identify if the issue is in:
1. State change detection
2. Event matching logic
3. DataFrame creation
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys

def load_db(db_path: Path):
    """Load database and convert to dataframe"""
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])
    except:
        df = [0]
        print(f'SQL read error for {db_path.name}')
    con.close()
    return df

# Parameters (from the state machine)
windowsize = 30
threshold = 0.6
halfwindow = int(windowsize / 2)

# Try to find a 2024 database file
db_path = Path('../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob("*.db")
test_file = None

for file in db_path:
    if len(file.name) < 18 and '20240711' in file.name and 'dgt2' in file.name:
        test_file = file
        break

if test_file is None:
    print("Could not find test file 20240711_dgt2.db")
    sys.exit(1)

print(f"Testing with: {test_file.name}")
print("=" * 60)

df = load_db(test_file)
if len(df) <= 1:
    print("Could not load data")
    sys.exit(1)

dgt = test_file.name[9:13]
date = test_file.name[:8]

ts = pd.to_datetime((1000 * 60 * 60 * 2) + df["timestamp"], unit='ms')

# Process only cell 4 for debugging
cell = 4
print(f"\nProcessing {date}, {dgt}, cell = {cell}")
print("=" * 60)

# Sliding median
median_vect = df.iloc[:, cell].rolling(windowsize).median()
print(f"Median vector length: {len(median_vect)}")
print(f"Median vector NaN count: {median_vect.isna().sum()}")

# State detection
state = np.where(median_vect > threshold, 1, 0)
print(f"\nState before padding - length: {len(state)}")
print(f"State value counts before padding:")
print(f"  0s: {np.sum(state == 0)}, 1s: {np.sum(state == 1)}")
print(f"First 50 state values: {state[:50]}")
print(f"Last 50 state values: {state[-50:]}")

# The problematic padding logic
state_padded = np.concatenate((state[halfwindow:], np.repeat(0, halfwindow)), axis=0)
print(f"\nState after padding - length: {len(state_padded)}")
print(f"State value counts after padding:")
print(f"  0s: {np.sum(state_padded == 0)}, 1s: {np.sum(state_padded == 1)}")
print(f"First 50 state values: {state_padded[:50]}")
print(f"Last 50 state values: {state_padded[-50:]}")

# State changes
statechange = pd.Series(state_padded).diff().fillna(0).astype("int")
print(f"\nState change analysis:")
print(f"Number of +1 transitions (ON): {np.sum(statechange == 1)}")
print(f"Number of -1 transitions (OFF): {np.sum(statechange == -1)}")
print(f"Other transitions: {np.sum((statechange != 0) & (statechange != 1) & (statechange != -1))}")

# Get event times
event_start_ts = ts[statechange == 1]
event_end_ts = ts[statechange == -1]
event_start_idx = df["timestamp"][statechange == 1]
event_end_idx = df["timestamp"][statechange == -1]

print(f"\nEvent extraction:")
print(f"Event_start_idx length: {len(event_start_idx)}")
print(f"Event_end_idx length: {len(event_end_idx)}")
print(f"Event_start_ts length: {len(event_start_ts)}")
print(f"Event_end_ts length: {len(event_end_ts)}")

# Create the dataframe (this is where duplicates might be created)
print(f"\nCreating DataFrame with:")
print(f"  Event_start: {len(list(event_start_idx))} items")
print(f"  Event_end: {len(list(event_end_idx))} items")
print(f"  Event_start_time: {len(list(event_start_ts))} items")
print(f"  Event_end_time: {len(list(event_end_ts))} items")

d = {"Event_start": list(event_start_idx),
    "Event_end": list(event_end_idx),
    "Event_start_time": list(event_start_ts),
    "Event_end_time": list(event_end_ts)}

event_list = pd.DataFrame(d)
print(f"\nResulting DataFrame shape: {event_list.shape}")
print(f"First 20 rows:")
print(event_list.head(20))

# Check for exact duplicate rows
print(f"\nDuplicate rows in DataFrame:")
duplicate_rows = event_list[event_list.duplicated(subset=['Event_start', 'Event_end', 'Event_start_time', 'Event_end_time'], keep=False)]
print(f"Number of rows with duplicates: {len(duplicate_rows)}")
if len(duplicate_rows) > 0:
    print("First few duplicates:")
    print(duplicate_rows.head(10))

print("\n" + "=" * 60)
print("Analysis complete. Check the output above for where duplicates originate.")
