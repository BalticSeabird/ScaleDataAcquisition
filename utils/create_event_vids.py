


import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
from pathlib import Path
import os

events = df_from_db("out/Events23-24.db", "event", "Event_start>0", "weight_median_tare>0.1", False)

# Build path to raw video
vid_path = "/mnt/BSP_NAS2/Video/"
output_path = "/mnt/BSP_NAS2_work/ ... "

row = events.iloc[0]

starttime = pd.to_datetime(row["start_time"])
endtime = pd.to_datetime(row["end_time"])
starttime_vid = starttime.floor(freq = "h")
datefold = str(format(starttime, "%Y-%m-%d"))
addseconds = 10 # Fixed add in the end and start
ledge = row["Scalename"]

if any(pd.isnull([starttime, endtime, starttime_vid])):
    print("skip")

else: 
    startsec = (starttime-starttime_vid)/np.timedelta64(1,'s')-addseconds
    endsec = (endtime-starttime_vid)/np.timedelta64(1,'s')+addseconds
   
    yrtext = starttime.year 
    vidformat_date = format(starttime_vid, "%Y-%m-%d_%H.%M.%S")
    full_path = f"{vid_path}Video{yrtext}/{ledge}/{datefold}/Auklab_{ledge}_{vidformat_date}.mp4"
    print(full_path)

    if os.path.isfile(full_path):
        tracknamex = row["track"]
        filename_out = f"{savepath}{tracknamex}.mp4"
        ffmpeg_extract_subclip(
            full_path,
            startsec,
            endsec,
            targetname = filename_out
        )
        #print(filename_out)
        return(filename_out)



