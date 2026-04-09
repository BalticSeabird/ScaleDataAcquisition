

# Runs in python 3.11.10

import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys
import os
import json
from datetime import datetime

# Add utils to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from functions import create_connection

def load_db(db_path: Path):           #load database and change into dataframe# 
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])  
    except: 
        df = [0]
        print(f'sql read error for {db_path.name}')
    con.close()
    return df   


#db_path = Path(f"C:/Users/Katharina/Documents/scaledata/{date}_{dgt}.db")
#db_path = Path(f'../../../../../../Volumes/JHS-SSD2/dgt/').rglob("*.db")
db_path = Path(f'../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob("*.db")


## New fast state machine

# Create output db 

# Delete old version if existing
if os.path.exists("out/Events23-25.db"):
    os.remove("out/Events23-25.db")

# Create empty db
con_local = create_connection("out/Events23-25.db")

# Set params
windowsize = 30
threshold = 0.6


# Time stamp
now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print("Start Time =", current_time)

# Initialize logging with structured format
total_files_processed = 0
total_cells_processed = 0
total_events_written = 0
files_log = []
start_time = current_time

for file in db_path:

    if len(file.name) < 18:
        df = load_db(file)
        if len(df) > 1:
            total_files_processed += 1
            print(file.name)

            file_log = {
                "file_number": total_files_processed,
                "filename": file.name,
                "dataframe_rows": len(df),
                "cells": []
            }

            dgt = file.name[9:13]
            date = file.name[:8]

            ts = pd.to_datetime((1000*60*60*2)+df["timestamp"], unit='ms')  #changes timestamp into local time#

            event_start = [] # Index for start event
            event_end = [] # Index for end event
            cell_save = [] # Index of cell
            date_save = []
            dgt_save = []
            j = 1

            while j <= 4:

                # Sliding median
                median_vect = df.iloc[:,j].rolling(windowsize).median()

                # on or of scale?
                halfwindow = int(windowsize/2)

                state = np.where(median_vect > threshold, 1, 0)
                state = np.concat((state[halfwindow:], np.repeat(0, halfwindow)), axis = 0)
                statechange = pd.Series(state).diff().fillna(0).astype("int")
                event_start = ts[statechange == 1]
                event_end = ts[statechange == -1]
                event_start_idx = df["timestamp"][statechange == 1]
                event_end_idx = df["timestamp"][statechange == -1]

                d = {"Event_start": list(event_start_idx),
                    "Event_end": list(event_end_idx),
                    "Event_start_time": list(event_start),
                    "Event_end_time": list(event_end)}
                event_list = pd.DataFrame(d)
                event_list["DGT"] = dgt
                event_list["cell"] = j
                event_list["db_name"] = file.name

                # Track events for structured logging
                events_this_cell = len(event_list)
                total_events_written += events_this_cell
                total_cells_processed += 1

                cell_log = {
                    "cell": j,
                    "iteration": total_cells_processed,
                    "event_count": events_this_cell
                }
                file_log["cells"].append(cell_log)

                event_list.to_sql("event", con_local, if_exists='append')
                print(f'{date}, {dgt}, cell = {j}')
                j += 1

            files_log.append(file_log)


# Time stamp
now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print("End Time =", current_time)

# Create structured debug report and save as JSON
debug_report = {
    "start_time": start_time,
    "end_time": current_time,
    "summary": {
        "total_files_processed": total_files_processed,
        "total_cells_processed": total_cells_processed,
        "expected_cells": total_files_processed * 4,
        "total_events_written": total_events_written,
        "average_events_per_cell": round(total_events_written / max(total_cells_processed, 1), 1),
        "cell_count_mismatch": total_cells_processed != total_files_processed * 4
    },
    "files": files_log
}

# Write JSON report
with open("state_machine_debug.json", "w") as f:
    json.dump(debug_report, f, indent=2)

# Also write human-readable text log for reference
with open("state_machine_debug.log", "w") as f:
    f.write(f"Start Time: {start_time}\n")
    f.write("="*80 + "\n\n")
    for file_info in files_log:
        f.write(f"FILE #{file_info['file_number']}: {file_info['filename']}\n")
        f.write(f"  DataFrame rows: {file_info['dataframe_rows']}\n")
        for cell_info in file_info['cells']:
            f.write(f"    Cell {cell_info['cell']} (iteration #{cell_info['iteration']}): {cell_info['event_count']} events\n")

    f.write("\n" + "="*80 + "\n")
    f.write("SUMMARY\n")
    f.write("="*80 + "\n")
    f.write(f"End Time: {current_time}\n")
    f.write(f"Total files processed: {debug_report['summary']['total_files_processed']}\n")
    f.write(f"Total cells processed: {debug_report['summary']['total_cells_processed']} (expected: {debug_report['summary']['expected_cells']})\n")
    f.write(f"Total events written: {debug_report['summary']['total_events_written']}\n")
    f.write(f"\nEvents per cell (average): {debug_report['summary']['average_events_per_cell']}\n")

    if debug_report['summary']['cell_count_mismatch']:
        f.write("\n⚠️  WARNING: Cell count mismatch!\n")
        f.write(f"Expected {debug_report['summary']['expected_cells']} cells (4 per file)\n")
        f.write(f"Got {debug_report['summary']['total_cells_processed']} cells\n")

print(f"\nDebug reports written to:")
print(f"  - state_machine_debug.json (structured)")
print(f"  - state_machine_debug.log (human-readable)")


