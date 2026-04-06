import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
from pathlib import Path
import os
import imageio_ffmpeg
import subprocess

events = df_from_db("out/Events23-25_weights.db", "event", "Event_start>0", "Sec_start>0.1", False)

# Base paths per year
vid_paths = {
    "2023": Path("../../../../../../mnt/BSP_NAS2/Video/Video2023/"),
    "2024": Path("../../../../../../mnt/BSP_NAS2/Video/Video2024/"),
    "2025": Path("../../../../../../mnt/BSP_NAS2_vol4/Video/Video2025/")
}

output_path = Path("../../../../../../mnt/BSP_NAS2_work/temp/eventvids_imageio2/")
output_path.mkdir(parents=True, exist_ok=True)


def extract_clip_ffmpeg(vidfile: Path, t1: int, t2: int, filename_out: Path) -> tuple[bool, str]:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    duration = max(1, t2 - t1)

    # First try stream-copy for speed.
    copy_cmd = [
        ffmpeg_exe,
        "-y",
        "-ss",
        str(t1),
        "-i",
        str(vidfile),
        "-t",
        str(duration),
        "-c",
        "copy",
        str(filename_out),
    ]
    copy_proc = subprocess.run(copy_cmd, capture_output=True, text=True)
    if copy_proc.returncode == 0 and filename_out.exists() and filename_out.stat().st_size > 1024:
        return True, "copy"

    # Fallback to re-encode when copy fails or creates a tiny invalid file.
    encode_cmd = [
        ffmpeg_exe,
        "-y",
        "-ss",
        str(t1),
        "-i",
        str(vidfile),
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(filename_out),
    ]
    encode_proc = subprocess.run(encode_cmd, capture_output=True, text=True)
    if encode_proc.returncode == 0 and filename_out.exists() and filename_out.stat().st_size > 1024:
        return True, "encode"

    err = (
        "ffmpeg copy failed with return code "
        f"{copy_proc.returncode}; ffmpeg encode failed with return code {encode_proc.returncode}"
    )
    return False, err

for rows in events.index: 

    row = events.iloc[rows]

    date = pd.to_datetime(row["Day"]) 
    yr = str(date.year)

    if yr not in vid_paths:
        print(f"Skipping unknown year: {yr}")
        continue

    vid_path = vid_paths[yr]

    datetext = date.strftime("%Y-%m-%d")
    ledge = row["Cameraname"]

    # Your logic simplified (np.where was redundant)
    secondsbefore = 5
    secondsafter = 15 if yr == "2023" else 5

    if pd.isnull(row["weight_median"]) or ledge == "BONDEN1":
        print("skip")
        continue

    startsec = row["Sec_start"] - secondsbefore
    endsec = row["Sec_end"] + secondsafter
    vidname = row["Video_path"]

    # Correct path construction
    vidfile = vid_path / ledge / datetext / vidname
    filename_out = output_path / f"{row['Event_ID']}.mp4"

    if filename_out.exists() and filename_out.stat().st_size > 1024:
        print(f"{filename_out} already exists, skipping")
        continue

    if vidfile.is_file():

        T1 = max(0, int(startsec))
        T2 = max(T1 + 1, int(endsec))
        
        try: 
            ok, method = extract_clip_ffmpeg(vidfile, T1, T2, filename_out)
            if ok:
                print(f'{filename_out} OK! ({method})')
            else:
                print(f'{filename_out} fail: {method}')

        except Exception as exc:
            print(f'{filename_out} fail: {exc}')
            continue

    else:    
        print(f'{vidfile} not found')
        print(" ")