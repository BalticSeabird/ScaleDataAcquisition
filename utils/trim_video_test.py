
import ffmpeg

vid = "../../../../../../Volumes/JHS-SSD2/scalevids/Auklab1_ROST2_SCALE_2024-07-20_07.00.00.mp4"
start_time = "00:33:49"
end_time = "00:34:26"

(
	ffmpeg.input(vid, ss=start_time, to=end_time)
	.output("../../../../../../Volumes/JHS-SSD2/rost2_2.mp4")
	.run()
)