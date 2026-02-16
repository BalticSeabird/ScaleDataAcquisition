

# Runs in python 3.11.10

import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys
import os
from functions import create_connection
from datetime import datetime

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


for file in db_path:

    if len(file.name) < 18:      
        df = load_db(file)
        if len(df) > 1: 
            print(file.name)
            
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
                event_list.to_sql("event", con_local, if_exists='append')
                print(f'{date}, {dgt}, cell = {j}')
                j += 1


# Time stamp
now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print("End Time =", current_time)


