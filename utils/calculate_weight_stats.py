

import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys
import os
from functions import create_connection
from datetime import datetime
import matplotlib.pyplot as plt
import warnings



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


# Delete old version if existing
if os.path.exists("out/Events23-24_weights1.db"):
    os.remove("out/Events23-24_weights1.db")


# Create empty db
con_local = create_connection("out/Events23-24_weights1.db")

# File with events 
events = load_db("out/Events23-24V3.db", "event")

# Scale names
lookup = pd.read_csv("temp/ScaleSystemNames.csv", sep = ";", parse_dates= ["Startdate", "Enddate"])



# List of databases to read raw weights from 
dbs = events["db_name"].unique()

# Params for weight events
tare_length = 10000 # ms
start_delay = 2000 # ms


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

    for row in event_info.index:
        start = event_info["Event_start"].loc[row]
        end = event_info["Event_end"].loc[row]
        cell = event_info["cell"].loc[row]
        cond1 = data["timestamp"] > start + start_delay
        cond2 = data["timestamp"] < end - start_delay
        cond3 = data["timestamp"] > start-tare_length
        cond4 = data["timestamp"] <= start
        cond5 = data["timestamp"] >= end
        cond6 = data["timestamp"] < end+tare_length
        data_event = data[cond1 & cond2][f"cell_{cell}"]
        data_before = data[cond3 & cond4][f"cell_{cell}"]
        data_after = data[cond5 & cond6][f"cell_{cell}"]
        
        if len(data_event) > 5:
            weight_med = data_event.median()
            weight_var.append(data_event.var())
            tare_before_median = data_before.median()
            tare_after_median = data_after.median()
            tare_average = (tare_before_median + tare_after_median)/2
            weight_median.append(weight_med - tare_average)
        else:
            weight_var.append(np.nan)
            weight_median.append(np.nan)

        # Add columns for weight data
    event_info["weight_median"] = weight_median
    event_info["weight_var"] = weight_var
    
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
        



# Make lineplot of weight data in data_before, data_event and data_after
# Save plot to file with event name

fig, ax = plt.subplots()
y = pd.concat([data_before, data_after])
ax.plot(y.index, y)
#ax.vlines(data_event.index[0], ymin = 0, ymax = 1, color = "red")
#ax.vlines(data_event.index[-1], ymin = 0, ymax = 1, color = "red") 
plt.savefig(f"out/figs/Event_example.png")