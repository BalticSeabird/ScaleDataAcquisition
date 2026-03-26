


import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
from pathlib import Path
import os
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import imageio_ffmpeg

events = df_from_db("out/Events23-25_weights.db", "event", "Event_start>0", "Sec_start>0.1", False)

# Build path to raw video

# General paths for the different years: 
vid_path_2023 = Path("../../../../../../mnt/BSP_NAS2/Video/Video2023/")
vid_path_2024 = Path("../../../../../../mnt/BSP_NAS2/Video/Video2024/")
vid_path_2025 = Path("../../../../../../mnt/BSP_NAS2_vol4/Video/Video2025/")

# Dictionary for video names in 2025
name_aliases_2025 = {
    "BJORN3TRI3_SCALE": "BJORN3TRI3_SCALE_ (192.168.1.110)",
    "FAR3_SCALE": "FAR3_SCALE_(192.168.1.161)",
    "FAR6BONDEN6_SCALE": "FAR6BONDEN6_SCALE_(192.168.1.147)",
    "TRI2_SCALE": "TRI2_SCALE _(192.168.1.161)",
    "TRI5_SCALE": "TRI5_SCALE_(192.168.1.161)",
}


output_path = "../../../../../../mnt/BSP_NAS2_work/temp/eventvids_imageio2/"
os.makedirs(output_path, exist_ok=True)

for rows in events.index: 

    row = events.iloc[rows]

    date = pd.to_datetime(row["Day"]) 
    yr = str(date.year)
    datetext = date.strftime("%Y-%m-%d")
    ledge = row["Cameraname"]
    secondsbefore = int(np.where(yr == "2023", 5, 5)) # Fixed add in the end and start
    secondsafter = int(np.where(yr == "2023", 15, 5)) # Fixed add in the end and start
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

            T1 = max(0, int(startsec))
            T2 = max(T1 + 1, int(endsec))
            
            try: 
                ffmpeg_extract_subclip(
                    vidfile,   
                    T1,
                    T2,
                    filename_out)
                
                print(f'{filename_out} OK!')

            except Exception as exc:
                print(f'{filename_out} fail: {exc}')
                continue

        else:    
            print(f'{vidfile} not found')
            print(" ")  



# Första minuten OK
# Slut = angivet slut minus start punkt?

# Funkar!
#(30, 0),
#(62, 0),