


import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
from pathlib import Path
import os
import ffmpeg

events = df_from_db("out/Events23-24.db", "event", "Cameraname!='BONDEN1'", "weight_median_tare>0.1", False)
events.sort_values(["Cameraname", "start_time"], inplace=True, ascending = False)

# Build path to raw video
vid_path = "../../../../../../mnt/BSP_NAS2/Video/"
output_path = "../../../../../../mnt/BSP_NAS2_work/temp/eventvids_ffmpeg/"
counter = 0

for rows in events.index: 
    counter += 1
    print(f'prossing row nr. {counter}')
    row = events.iloc[rows]

    secondsbefore = 2 # Fixed add in the end and start
    secondsafter = 6 # Fixed add in the end and start
    start = pd.to_datetime(row["start_time"])-pd.Timedelta(seconds = secondsbefore)
    end = pd.to_datetime(row["end_time"])+pd.Timedelta(seconds = secondsafter)
    starthr = int(format(start, "%H"))
    endhr = int(format(end, "%H"))
    starttime = format(start, "00:%M:%S")
    if endhr > starthr: 
        endtime = "00:59:59"
    else: 
        endtime = format(end, "00:%M:%S")
    starttime_vid = start.floor(freq = "h")
    datefold = str(format(start, "%Y-%m-%d"))
    secondsbefore = 2 # Fixed add in the end and start
    secondsafter = 2 # Fixed add in the end and start
    ledge = row["Cameraname"]

    if any(pd.isnull([starttime, endtime, starttime_vid])) or ledge == "BONDEN1":
        print("skip")

    else: 
        #startsec = (starttime-starttime_vid)/np.timedelta64(1,'s')-secondsbe
        #endsec = (endtime-starttime_vid)/np.timedelta64(1,'s')+secondsafter
    
        yrtext = start.year 
        vidformat_date = format(starttime_vid, "%Y-%m-%d_%H.%M.%S")
        full_path = f"{vid_path}Video{yrtext}/{ledge}/{datefold}/Auklab1_{ledge}_{vidformat_date}.mp4"
        print(full_path)
        tracknamex = f'{row["Cameraname"]}_{row["Date"]}_{row["Event_start"]}'
        filename_out = f"{output_path}{tracknamex}.mp4"
        
        if os.path.isfile(full_path):
            if os.path.isfile(filename_out) == False:
                        
                (
                    ffmpeg.input(full_path, ss=starttime, to=endtime)
                    .output(filename_out)
                    .run()
                )
                
            print(f'{filename_out} OK!')
