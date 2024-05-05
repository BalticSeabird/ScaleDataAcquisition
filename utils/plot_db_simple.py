"""
Example: 
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys

def load_db(db_path: Path):
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])
    con.close()
    return df


dgt = "dgt1"
date = "20240504"
yr = int(date[0:4])

db_path = Path(f"/home/bsp/Documents/Weight_logger/{dgt}/backup/{date}/{date}_{dgt}.db")
#db_path = Path(f"data/{dgt}/{date}_{dgt}.db")

print(db_path)

yrs = list(np.repeat([2023, 2024], 8))
dgts = list(np.tile(list(np.repeat(["dgt1", "dgt2"], 4)), 2))
cells = list(np.tile(["cell_1", "cell_2", "cell_3", "cell_4"], 4))
scales = ["FAR8D_BOX", "BONDEN1", "TLZOOM", "FAR3_SCALE", 
         "FAR3BONDEN3_SCALE", "BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "FAR6_SCALE", 
         "FAR8D_BOX", "BONDEN1", "FAR3_SCALE", "FAR6_SCALE", 
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

ts = pd.to_datetime((1000*60*60*2)+df["timestamp"], unit='ms')

for i in range(4):
    column = "cell_"+str((i+1)) 
    ax[i].plot(ts,df[column])
    ax[i].set_title(names.iloc[i])
    ax[i].grid(True)
#fig.tight_layout(pad=2.0)
plt.show()



sys.exit()

sl_mean = []
sl_std = []
event_start = []

event_detected = False
for i in range(100, (len(df)-100)):
    sl_mean.append(np.mean(df.iloc[i-100:i]["cell_1"]))
    sl_std.append(np.std(df.iloc[i-100:i]["cell_1"]))
    if df.iloc[i]["cell_1"] - sl_mean[-1] > 6*sl_std[-1] and event_detected == False:
        print('start event detected at frame ', i)
        event_detected = True
        event_start.append(i)
    if sl_mean[-1] - df.iloc[i]["cell_1"] > 6*sl_std[-1] and event_detected == True:
        print('end event detected at frame ', i)
        event_detected = False
    if i % 10000 == 0:
        print(i)


