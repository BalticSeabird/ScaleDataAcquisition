import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import csv
import sys
from datetime import datetime as dt
import os

#path = "C:/Users/Katharina/Documents/scaledata/2024/"
path = "/Users/jonas/Documents/temp/output/"

files = Path(path).rglob("*.db")

for file in files:
            
    con = sqlite3.connect(file)
    df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])  
    
    dgt = file.name[9:13]
    date = file.name[:8]
    yr = file.name[:4]

    # Check if files has been processed already
    filename_save = f'Event_data_{dgt}_{date}.csv' 
    
    if os.path.exists(f'out/{filename_save}'):

        print(f'{filename_save} already processed - continue with next file ...')
    
    else: 
        ts = pd.to_datetime((1000*60*60*2)+df["timestamp"], unit='ms')  #changes timestamp into local time#

        event_start = [] # Index for start event
        event_end = [] # Index for end event 
        cell_save = [] # Index of cell 
        date_save = [] 
        dgt_save = []
        event_detected = False
        j = 1 

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

        if len(event_end) < len(event_start):   
            event_end.append(i)      # If there is no end of an event, add it manually (final time stamp)

        d = {"DGT": dgt_save,
            "Date": date_save, 
            "Cell": cell_save, 
            "Event_start": event_start, 
            "Event_end": event_end,
            "start_time": list(ts[event_start]),
            "end_time": list(ts[event_end])} 
        event_list = pd.DataFrame(d)

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
            #fig, ax = plt.subplots()
            #x = range(tare_before_data.index[0], 1+tare_after_data.index[-1])
            #y = pd.concat([tare_before_data, weight_data, tare_after_data])
            #ax.plot(x, y)
            #ax.hlines(weight_median[-1],event_start,event_end, color = "blue")
            #ax.hlines(tare_bef_median[-1],event_start-100,event_start, color = "red")
            #ax.hlines(tare_after_median[-1],event_end,event_end+100, color = "red")
            #plotname = f'{dgt}_{date}_cell_{cell}_{event_start}'
            #plt.suptitle(plotname)
            #plt.title(f'Tared median weight = {weight_current} gram, event length = {event_length} data points')
            #plt.savefig(f'out/{plotname}.png', dpi = 300)
            #plt.close()


        event_list["weight_median"] = weight_median
        event_list["weight_mean"] = weight_mean
        event_list["tare_bef_median"] = tare_bef_median
        event_list["tare_after_median"] = tare_after_median
        event_list["tare_average"] = tare_average
        event_list["weight_median_tare"] = weight_median_tare

        event_list.to_csv(f'out/{filename_save}', sep = ";", decimal = ",")





       








