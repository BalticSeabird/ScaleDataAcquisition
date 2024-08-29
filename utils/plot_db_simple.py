"""
Example: 
"""

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


dgt = "dgt1"                    
date = "20240605"
yr = int(date[0:4])

db_path = Path(f"C:/Users/Katharina/Documents/scaledata/{date}_{dgt}.db")
#db_path = Path(f"data/{dgt}/{date}_{dgt}.db")

print(db_path)

yrs = list(np.repeat([2023, 2024], 8))
dgts = list(np.tile(list(np.repeat(["dgt1", "dgt2"], 4)), 2))
cells = list(np.tile(["cell_1", "cell_2", "cell_3", "cell_4"], 4))
scales = ["FAR8D_BOX", "BONDEN1", "TLZOOM", "FAR3_SCALE", 
         "FAR3BONDEN3_SCALE", "BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "FAR6_SCALE", 
         "FAR6_SCALE", "BONDEN1", "FAR8D_SCALE", "FAR3_SCALE", 
         "FAR3BONDEN3_SCALE", "BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "ROST2_SCALE",]

d = {"Yr": yrs, "dgt": dgts, "cell": cells, "scale": scales} 
lookup = pd.DataFrame(d)

# Names for plotting
cond1 = lookup["Yr"] == yr
cond2 = lookup["dgt"] == dgt
names = lookup[cond1 & cond2]["scale"]


## RUN

# Load database
df = load_db(db_path)

# PLOT
fig, ax = plt.subplots(4)

ts = pd.to_datetime((1000*60*60*2)+df["timestamp"], unit='ms')  #changes timestamp into local time#

for i in range(0,4):
    column = "cell_"+str((i+1)) 
    ax[i].plot(ts,df[column])
    ax[i].set_title(names.iloc[i])
    ax[i].grid(True)
#fig.tight_layout(pad=2.0)
plt.show()


#sys.exit()

#sl_mean = []
#sl_std = []
#event_start = []
#event_end = [] 

#event_detected = False
#for i in range(100, (len(df)-100)):
 #   sl_mean.append(np.mean(df.iloc[i-100:i]["cell_3"]))
  #  sl_std.append(np.std(df.iloc[i-100:i]["cell_3"]))
   # if df.iloc[i]["cell_3"] - sl_mean[-1] > 11*sl_std[-1] and event_detected == False:
    #    print('start event detected at frame ', i)
     #   event_detected = True
      #  event_start.append(i)
    #if sl_mean[-1] - df.iloc[i]["cell_3"] > 11*sl_std[-1] and event_detected == True:
     #   print('end event detected at frame ', i)
      #  event_detected = False
       # event_end.append(i)
    #if i % 10000 == 0:
     #   print(i)



sl_mean = []
sl_std = []
event_start = []
event_end = [] 

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
    j = j + 1

#plot actual events and detected events in one plot
#new try:#
#plottet die vier verschiedenen Waagen, aber jeweils alle events in alle plots#

j = 1

while j <= 4:
    fig, ax = plt.subplots()
    ax.plot(df.index,df["cell_"+str(j)])

    for i in event_start:
        ax.vlines(i,-0.2,1, color = "black")

    for i in event_end:
        ax.vlines(i,-0.2,1, color = "red")

    plt.show()
    j = j+1

#sys.exit()

#old, working version:#

#fig, ax = plt.subplots()
#ax.plot(df.index,df["cell_1"])

#for i in event_start:
    #ax.vlines(i,-0.2,1, color = "black")

#for i in event_end:
    #ax.vlines(i,-0.2,1, color = "red")

#plt.show()

median_weight = []
tare_before = []
j = 1

while j <= 4:
    all_events = range(0, len(event_start))
    for event in all_events:
        start = event_start[event]
        end = event_end[event]
        median_weight.append(np.median(df.iloc[start:end]["cell_"+str(j)]))
        tare_before.append(np.median(df.iloc[(start-100):(start-1)]["cell_"+str(j)]))
    j = j + 1

# Create dictionary, working version:
#d = {"event_num": list(all_events), 
 #   "start_time": list(ts[event_start]), 
  #  "end_time": list(ts[event_end]), 
   # "tare_before": tare_before, 
    #"median_weight": median_weight,
    #"index_start": event_start, 
    #"index_end": event_end 
    #}

#dfx = pd.DataFrame(d, index = list(all_events))
    
#dfx["scale"] = "cell_1"
#dfx["date"] = dfx["time"].dt.date  #using this gives an error# 
#dfx["event_id"] = dfx["scale"]+"_"+dfx["date"].astype(str)+"_"+dfx["event_num"].astype(str)

#dfx.to_csv("out/events_dgt1_20240605.csv")

d = {"event_num": list(all_events), 
    "start_time": list(ts[event_start]), 
    "end_time": list(ts[event_end]), 
    "tare_before": tare_before, 
    "median_weight": median_weight,
    }                                       #wie ordne ich die events den cells zu?

dfx = pd.DataFrame(d)

dfx.to_csv("out/weight_events_dgt1_20240605.csv")