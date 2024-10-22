
import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
from pathlib import Path
import os


# Lookup table for scale names
lookup = pd.read_csv("temp/ScaleSystemNames.csv", sep = ";", parse_dates= ["Startdate", "Enddate"])

interval = []
for row in lookup.index:
    start = lookup["Startdate"][row]
    end = lookup["Enddate"][row]+pd.Timedelta(days = 1)
    interval.append(pd.Interval(start, end, closed = "neither"))

lookup["Interval"] = interval


# All event files
files = Path("out/").glob("*.csv")


# Delete old version of local db
if os.path.exists("out/Events23-24.db"):
    os.remove("out/Events23-24.db")

# Create empty db
con_local = create_connection("out/Events23-24.db")

for file in files: 

    t1 = pd.read_csv(file, sep = ";", parse_dates= ["start_time"])

    if len(t1) > 0: 

        # Pick out matching dates (only first row of data) 
        time = t1["start_time"][0]
        inside = []
        for row in lookup.index: 
            if time in lookup["Interval"][row]:
                inside.append(1)
            else: 
                inside.append(0) 

        lookup["Inside"] = inside
        lookup_reduced = lookup[lookup["Inside"] == 1]

        # Merge based on date, dgt name and cell num
        t2 = t1.merge(lookup_reduced[["DGT", "Cell", "Scalename"]], on = ["DGT", "Cell"], how = "left")

        t2.to_sql("event", con_local, if_exists='append')






