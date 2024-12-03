

from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip


vidfile = "../../../../../../mnt/BSP_NAS2/Video/Video2024/FAR6_SCALE/2024-06-06/Auklab1_FAR6_SCALE_2024-06-06_10.00.00.mp4"
filename_out = "out/testvid.mp4"

count = 0 
while count < 3:
    try: 
        ffmpeg_extract_subclip(
            vidfile,   
            0,
            100,
            filename_out)
    except: 
        print("video fail")
        continue
    count += 1
    print(count)

