


import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
from pathlib import Path
import os
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

events = df_from_db("out/Events23-24.db", "event", "Event_start>0", "weight_median_tare>0.1", False)
#events = df_from_db("out/Events23-24.db", "event", "Cell>0", "Cell>0.1", False)

# Build path to raw video
vid_path = "../../../../../../mnt/BSP_NAS2/Video/"
output_path = "../../../../../../mnt/BSP_NAS2_work/temp/eventvids/"

for rows in events.index: 

    row = events.iloc[rows]

    starttime = pd.to_datetime(row["start_time"])
    endtime = pd.to_datetime(row["end_time"])
    starttime_vid = starttime.floor(freq = "h")
    datefold = str(format(starttime, "%Y-%m-%d"))
    secondsbefore = -5 # Fixed add in the end and start
    secondsafter = 25 # Fixed add in the end and start
    ledge = row["Cameraname"]

    if any(pd.isnull([starttime, endtime, starttime_vid])) or ledge == "BONDEN1":
        print("skip")

    else: 
        startsec = (starttime-starttime_vid)/np.timedelta64(1,'s')-secondsbefore
        endsec = (endtime-starttime_vid)/np.timedelta64(1,'s')+secondsafter
    
        yrtext = starttime.year 
        vidformat_date = format(starttime_vid, "%Y-%m-%d_%H.%M.%S")
        full_path = f"{vid_path}Video{yrtext}/{ledge}/{datefold}/Auklab1_{ledge}_{vidformat_date}.mp4"
        print(full_path)

        if os.path.isfile(full_path):
            tracknamex = f'{row["Cameraname"]}_{row["Date"]}_{row["Event_start"]}'
            filename_out = f"{output_path}{tracknamex}.mp4"
            ffmpeg_extract_subclip(
                full_path,
                startsec,
                endsec,
                targetname = filename_out
            )
            print(f'{filename_out} OK!')


