


import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
from pathlib import Path
import os
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import imageio_ffmpeg

events = df_from_db("out/Events23-24_weights1.db", "event", "Event_start>0", "Sec_start>0.1", False)

# Build path to raw video
vid_path = Path("../../../../../../mnt/BSP_NAS2/Video/")
output_path = "../../../../../../mnt/BSP_NAS2_work/temp/eventvids_imageio2/"

for rows in events.index: 

    row = events.iloc[rows]

    date = pd.to_datetime(row["Day"]) 
    yr = str(date.year)
    datetext = date.strftime("%Y-%m-%d")
    ledge = row["Cameraname"]
    secondsbefore = -5 # Fixed add in the end and start
    secondsafter = 5 # Fixed add in the end and start
    ledge = row["Cameraname"]

    if pd.isnull(row["weight_median"]) or ledge == "BONDEN1":
        print("skip")

    else: 
        startsec = row["Sec_start"]-secondsbefore
        endsec = row["Sec_end"]+secondsafter
        vidname = row["Video_path"]

        vidfile = f"{vid_path}/Video{yr}/{ledge}/{datetext}/{vidname}"
        filename_out = output_path+row["Event_ID"]+".mp4"

        if os.path.isfile(vidfile):

            T1, T2 = [int(t) for t in [startsec, endsec]]
            
            ffmpeg_extract_subclip(
                vidfile,   
                T1,
                T1+T2,
                filename_out)
            
            print(f'{filename_out} OK!')
            
        else:    
            print(f'{vidfile} not found')
            print(" ")  



# Första minuten OK
# Slut = angivet slut minus start punkt?

# Funkar!
#(30, 0),
#(62, 0),