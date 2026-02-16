
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


dgt = sys.argv[1] #"dgt2"                    
date = sys.argv[2] # "20230615"
yr = int(date[0:4])
filename = f'{date}_{dgt}.db'


db_path = Path(f'../../../../Downloads/{date}_{dgt}_recovered.db')
#db_path = list(Path(f'../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(filename))[0]
#db_path = list(Path(f'../../../../../../Volumes/JHS-SSD2/dgt/').rglob(filename))[0]
#db_path = Path(f"C:/Users/Katharina/Documents/scaledata/{date}_{dgt}.db")
#db_path = Path(f'../../../../../../Volumes/JHS-SSD2/dgt/{yr}/backup/{date}/{date}_{dgt}.db')
#db_path = Path(f'../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/{yr}/{dgt}/{date}/{date}_{dgt}.db')

## Load database with raw data readings
df = load_db(db_path)


## Time stamp
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

plt.suptitle(f'{dgt}_{date}')

plt.show()
#plt.savefig("out/figs/test.png")


