import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import csv
import sys

#defines function to load database from defined path and change into dataframe, selects all columns from the table cells#
#sorts them by timestamp#
#columns are: timestamp, cell 1, cell 2, cell 3, cell 4#

def load_db(db_path: Path):           
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])  
    con.close()
    return df   

#load database#

dgt = "dgt1"                    
date = "20240605"
yr = int(date[0:4])

db_path = Path(f"C:/Users/Katharina/Documents/scaledata/{date}_{dgt}.db")
df = load_db(db_path)

#defines variables#

yrs = list(np.repeat([2023, 2024], 8))
dgts = list(np.tile(list(np.repeat(["dgt1", "dgt2"], 4)), 2))
cells = list(np.tile(["cell_1", "cell_2", "cell_3", "cell_4"], 4))
scales = ["FAR8D_BOX", "BONDEN1", "TLZOOM", "FAR3_SCALE", 
         "FAR3BONDEN3_SCALE", "BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "FAR6_SCALE", 
         "FAR6_SCALE", "BONDEN1", "FAR8D_SCALE", "FAR3_SCALE", 
         "FAR3BONDEN3_SCALE", "BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "ROST2_SCALE",]

d = {"Yr": yrs, "dgt": dgts, "cell": cells, "scale": scales} 
lookup = pd.DataFrame(d)

# Names for plotting  (??)
cond1 = lookup["Yr"] == yr
cond2 = lookup["dgt"] == dgt
names = lookup[cond1 & cond2]["scale"]

#Plot#

fig, ax = plt.subplots(4)

ts = pd.to_datetime((1000*60*60*2)+df["timestamp"], unit='ms')  #changes timestamp into local time#

for i in range(0,4):
    column = "cell_"+str((i+1)) 
    ax[i].plot(ts,df[column])
    ax[i].set_title(names.iloc[i])
    ax[i].grid(True)
#plt.show()

#detect weight events and calculate median weight and tare before#

#csv_file_name = "events_dgt1_20240605.csv"

#with open(csv_file_name,'a', newline='', encoding = 'utf-8') as c: 
 #   writer = csv.writer(c)
  #  writer.writerow (['Start_time', 'End_time', 'tare_before', 'median_weight', 'cell'])


sl_mean = []
sl_std = []
event_start = []
event_end = [] 
median_weight = []
tare_before = []
scale = []
   

event_detected = False
j = 1

while j <= 4:
    for i in range(100, (len(df)-100)):
        sl_mean.append(np.mean(df.iloc[i-100:i]["cell_"+str(j)]))
        sl_std.append(np.std(df.iloc[i-100:i]["cell_"+str(j)]))
        if df.iloc[i]["cell_"+str(j)] - sl_mean[-1] > 0.5 and event_detected == False:
            print('start event detected at frame ', i)
            event_detected = True
            event_start.append(i)
        if sl_mean[-1] - df.iloc[i]["cell_"+str(j)] > 0.5 and event_detected == True:
            print('end event detected at frame ', i)
            event_detected = False
            event_end.append(i)
        if i % 10000 == 0:
            print(i)
    all_events = range(0, len(event_start))
    for event in all_events:
        start = event_start[event]
        end = event_end[event]
        median_weight.append(np.median(df.iloc[start:end]["cell_"+str(j)]))
        tare_before.append(np.median(df.iloc[(start-100):(start-1)]["cell_"+str(j)]))
        scale.append("cell_"+str(j))
    
    d = {"event_num": list(all_events), 
        "start_time": list(ts[event_start]), 
        "end_time": list(ts[event_end]), 
        "tare_before": list(tare_before), 
        "median_weight": list(median_weight),
        "scale": list(scale),
        }                                             

    dfx = pd.DataFrame(d)
    dfx.to_csv("out/weight_events_dgt1_20240605.csv")

    j = j + 1








