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

#db_path = Path(f"C:/Users/Katharina/Documents/scaledata/{date}_{dgt}.db")
db_path = Path(f'/Users/jonas/Documents/temp/output/{dgt}/backup/{date}/{date}_{dgt}.db')

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


## Load database
df = load_db(db_path)

## Simple plot of time series of raw data for the four cells
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



## State machine for finding and saving events for the different load cells (scales) 

#sl_mean = []
#sl_std = [] 
event_start = [] # Index for start event
event_end = [] # Index for end event 
cell_save = [] # Index of cell 
date_save = [] 
dgt_save = []
event_detected = False
j = 1 # Index of the scale

while j <= 4:
    for i in range(100, (len(df)-100)):
#    for i in range(100000, 200000):
        sl_mean = np.mean(df.iloc[i-100:i]["cell_"+str(j)])
        #sl_std = np.std(df.iloc[i-100:i]["cell_"+str(j)])
        if df.iloc[i]["cell_"+str(j)] - sl_mean > 0.5 and event_detected == False:
            print('start event detected at frame ', i)
            event_detected = True
            event_start.append(i)
            cell_save.append(j)
            date_save.append(date)
            dgt_save.append(dgt)
        if sl_mean - df.iloc[i]["cell_"+str(j)] > 0.5 and event_detected == True:
            print('end event detected at frame ', i)
            event_detected = False
            event_end.append(i)
        if i % 10000 == 0:
            print(f'processing {date}, {dgt}, scale {j}, row {i} ...')
    j = j + 1


# Create a Data frame of events
d = {"DGT": dgt_save,
    "Date": date_save, 
    "Cell": cell_save, 
    "Event_start": event_start, 
    "Event_end": event_end} 
event_list = pd.DataFrame(d)

## Calculate statistics for each detected event, and save plots 
weight_median = []
weight_mean = []
tare_bef_median = []
tare_after_median = [] 
tare_average = []
weight_median_tare = []
for row in event_list.index: 
    event_data = event_list.iloc[row]
    cell = event_data["Cell"]
    event_start = event_data["Event_start"]
    event_end = event_data["Event_end"]
    weight_data = df.iloc[range(event_start, event_end)][f'cell_{cell}']
    tare_before_data = df.iloc[range((event_start-100), event_start)][f'cell_{cell}']
    tare_after_data = df.iloc[range(event_end, (event_end+100))][f'cell_{cell}']
    weight_mean.append(np.mean(weight_data))
    weight_median.append(np.median(weight_data))
    tare_bef_median.append(np.median(tare_before_data))
    tare_after_median.append(np.median(tare_after_data))
    tare_average.append(np.mean([tare_bef_median[-1], tare_after_median[-1]]))
    event_length = event_end-event_start
    weight_current = np.round(weight_median[-1] - tare_average[-1], 3)
    weight_median_tare.append(weight_current)
    # Save plots within loop for inspecting results  
    fig, ax = plt.subplots()
    x = range(tare_before_data.index[0], 1+tare_after_data.index[-1])
    y = pd.concat([tare_before_data, weight_data, tare_after_data])
    ax.plot(x, y)
    ax.hlines(weight_median[-1],event_start,event_end, color = "blue")
    ax.hlines(tare_bef_median[-1],event_start-100,event_start, color = "red")
    ax.hlines(tare_after_median[-1],event_end,event_end+100, color = "red")
    plotname = f'{dgt}_{date}_cell_{cell}_{event_start}'
    plt.suptitle(plotname)
    plt.title(f'Tared median weight = {weight_current} gram, event length = {event_length} data points')
    plt.savefig(f'output/plots/{plotname}.png', dpi = 300)
    plt.close()


## Save output 
event_list["weight_median"] = weight_median
event_list["weight_mean"] = weight_mean
event_list["tare_bef_median"] = tare_bef_median
event_list["tare_after_median"] = tare_after_median
event_list["tare_average"] = tare_average
event_list["weight_median_tare"] = weight_median_tare

event_list.to_csv(f'output/event_data/Event_data_{dgt}_{date}.csv', sep = ";", decimal = ",")

#plot actual events and detected events in one plot
#new try:#
#plottet die vier verschiedenen Waagen, aber jeweils alle events in alle plots#


sys.exit()

#### AFTER HERE, I HAVE NOT LOOKED AT THE CODE! JHS 2 SEPT 2024. 



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