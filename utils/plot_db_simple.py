
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


dgt = "dgt1"                    
date = "20240718"
yr = int(date[0:4])

#db_path = Path(f"C:/Users/Katharina/Documents/scaledata/{date}_{dgt}.db")
db_path = Path(f'../../../../../../Volumes/JHS-SSD2/dgt/{yr}/{dgt}/{date}/{date}_{dgt}.db')
#db_path = Path(f'../../../../../../Volumes/JHS-SSD2/dgt/{yr}/backup/{date}/{date}_{dgt}.db')
#db_path = Path(f'../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/{yr}/{dgt}/{date}/{date}_{dgt}.db')

## Load database with raw data readings
df = load_db(db_path)


## Load db with events
df_events = load_db2("out/Events23-24.db")
df_events["start_time"] = pd.to_datetime(df_events["start_time"], format = "mixed")
df_events["end_time"] = pd.to_datetime(df_events["end_time"])
df_events["Date2"] = df_events["Date"].astype("str")
cond1 = df_events["DGT"] == dgt
cond2 = df_events["Date2"] == date

df_events = df_events[cond1 & cond2]

## Time stamp
## OBS, not starting 00:00, something wrong already here?
## 1 min 14 seconds off...
df["time"] = pd.to_datetime((1000*60*60*2)+df["timestamp"], unit='ms')  #changes timestamp into local time#


# Lookup table for scale names
lookup = pd.read_csv("temp/ScaleSystemNames.csv", sep = ";", parse_dates= ["Startdate", "Enddate"])

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



## New faster (?) state machine
i = 4
windowsize = 30
windowsize_tare = 100000
threshold = 0.6

# Sliding median 
median_vect = df.iloc[:,i].rolling(windowsize).median()

# Long Rolling min filter for tare 
#min_long_forward = median_vect.rolling(windowsize_tare).min()
#min_long_backward = median_vect.iloc[::-1].reindex().rolling(windowsize_tare).min()

#bw = median_vect.iloc[::-1]
#index = bw.index
#new_index = range(index[-1], index[0]+1)
#bw_reindexed = pd.Series(bw, index = new_index)


# on or of? 
halfwindow = int(windowsize/2)
halfwindow_tare = int(windowsize_tare/2)

state = np.where(median_vect > threshold, 1, 0)
state = np.concat((state[halfwindow:], np.repeat(0, halfwindow)), axis = 0)
statechange = pd.Series(state).diff()
event_starts = df[statechange == 1]["time"]
event_ends = df[statechange == -1]["time"]

## Plot one at the time

fig, ax = plt.subplots()
startstop = int(windowsize/2)
ax.plot(df["time"], df.iloc[:,i])
#ax.plot(df["time"].iloc[:-startstop], median_vect.iloc[startstop:], color = "red")
ax.plot(df["time"], min_long_forward, color = "red")
#ax.plot(df["time"], bw_reindexed, color = "brown")
name = df.iloc[:,i].name
ax.set_title(name)
evdat = df_events[df_events["Cameraname"] == name].reset_index()
#ax.vlines(event_starts, ymin = 0, ymax = 1, color = "green")
#ax.vlines(event_ends, ymin = 0, ymax = 1, color = "violet")

plt.show()




## Simple plot of time series of raw data for the four cells
fig, ax = plt.subplots(4)
for i in range(1,5):
    ax[(i-1)].plot(df["time"], df.iloc[:,(i)])
    name = df.iloc[:,(i)].name
    ax[(i-1)].set_title(name)
    evdat = df_events[df_events["Cameraname"] == name].reset_index()
    for j in evdat.index:
        ax[(i-1)].vlines(x = evdat.iloc[j]["start_time"], ymin = 0, ymax = 1, colors = "green")
        ax[(i-1)].vlines(x = evdat.iloc[j]["end_time"], ymin = 0, ymax = 1, colors = "red")

plt.suptitle(f'{dgt}_{date}')

plt.show()






    # Get matching event data
 