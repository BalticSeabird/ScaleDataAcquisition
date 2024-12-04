
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys

def load_db(db_path: Path):           #load database and change into dataframe# 
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])  
    con.close()
    return df   

def load_db2(db_path: Path):           #load database and change into dataframe# 
    con = sqlite3.connect(db_path)
    sql = ("SELECT * FROM event")       
    df = pd.read_sql_query(sql, con)
    con.close()
    return df   


dgt = "dgt2"                    
date = "20230615"
yr = int(date[0:4])
filename = f'{date}_{dgt}.db'

#db_path = list(Path(f'../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(filename))[0]
db_path = list(Path(f'../../../../../../Volumes/JHS-SSD2/dgt/').rglob(filename))[0]
#db_path = Path(f"C:/Users/Katharina/Documents/scaledata/{date}_{dgt}.db")
#db_path = Path(f'../../../../../../Volumes/JHS-SSD2/dgt/{yr}/backup/{date}/{date}_{dgt}.db')
#db_path = Path(f'../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/{yr}/{dgt}/{date}/{date}_{dgt}.db')

## Load database with raw data readings
df = load_db(db_path)


## Load db with events
df_events = load_db2("out/Events23-24_weights1.db")
df_events["Event_start_time"] = pd.to_datetime(df_events["Event_start_time"], format = "mixed")
df_events["Event_end_time"] = pd.to_datetime(df_events["Event_end_time"], format = "mixed")

df_events["Event_start_time_corr"] = df_events["Event_start_time"]+pd.Timedelta(hours = 2)
df_events["Event_end_time_corr"] = df_events["Event_end_time"]+pd.Timedelta(hours = 2)

df_events["Day"] = [format(df_events["Event_start_time"].loc[row], "%Y%m%d") for row in df_events.index]  
cond1 = df_events["DGT"] == dgt
cond2 = df_events["Day"] == date

df_events = df_events[cond1 & cond2]

## Time stamp
## OBS, not starting 00:00, something wrong already here?
## 1 min 14 seconds off...
df["time"] = pd.to_datetime((1000*60*60*2)+df["timestamp"], unit='ms')  #changes timestamp into local time#


# Assign correct scale names to rows
lookup = pd.read_csv("temp/ScaleSystemNames.csv", sep = ";", parse_dates=["Startdate", "Enddate"])
interval = []
for row in lookup.index:
    start = lookup["Startdate"][row]
    end = lookup["Enddate"][row]+pd.Timedelta(days = 1)
    interval.append(pd.Interval(start, end, closed = "neither"))

lookup["Interval"] = interval

# Pick out matching dates (only first row of data) 
time = df["time"][0]
inside = []
for row in lookup.index: 
    if time in lookup["Interval"][row]:
        inside.append(1)
    else: 
        inside.append(0) 

lookup["Inside"] = inside
cond1 = lookup["Inside"] == 1
cond2 = lookup["DGT"] == dgt
lookup_reduced = lookup[cond1 & cond2]
lookup_reduced = lookup_reduced.sort_values(["Cell"])
names = lookup_reduced["Cameraname"]

# Merge based on date, dgt name and cell num
df.rename(columns={'cell_1': names.iloc[0],'cell_2':names.iloc[1],'cell_3': names.iloc[2],'cell_4':names.iloc[3]},inplace=True)


def halftime(a, b): 
    length = b-a
    c = a + length/2
    return(c)


## Simple plot of time series of raw data for the four cells
fig, ax = plt.subplots(4)
for i in range(1,5):
    ax[(i-1)].plot(df["time"], df.iloc[:,(i)])
    name = df.columns[i]
    ax[(i-1)].set_title(name)
    evdat = df_events[df_events["Cameraname"] == name]
    for j in evdat.index:
        a = evdat.loc[j]["Event_start_time"]
        b = evdat.loc[j]["Event_end_time"]
        eventID = evdat.loc[j]["Event_ID"]
        weight = round(evdat.loc[j]["weight_median"], 2)
        weight_var = round(1000*evdat.loc[j]["weight_var"], 2)
        midtime = halftime(a, b)
        ax[(i-1)].vlines(x = a, ymin = 0, ymax = 1, colors = "green")
        ax[(i-1)].vlines(x = b, ymin = 0, ymax = 1, colors = "red")
        ax[(i-1)].text(a, .6, a, horizontalalignment = "center", fontsize = 8)
        ax[(i-1)].text(b, .5, b, horizontalalignment = "center", fontsize = 8)
        ax[(i-1)].text(midtime, .4, eventID, horizontalalignment = "center", fontsize = 8)
        ax[(i-1)].text(midtime, .3, f'median weight = {weight}', horizontalalignment = "center", fontsize = 8)
        ax[(i-1)].text(midtime, .2, f'weighing stability = {weight_var}', horizontalalignment = "center", fontsize = 8)

plt.suptitle(f'{dgt}_{date}')

plt.show()
#plt.savefig("out/figs/test.png")


