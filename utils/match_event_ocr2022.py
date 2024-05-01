



import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
import pickle
import matplotlib.pyplot as plt



# For 2022 data
ocr22 = df_from_db("output/ocr/TLZOOM_2022_read_ring_tag.db", "events", "number_of_detections>0", "number_of_detections>0", False)
starttime = []
endtime = []
start = starttime.append([(i).split("/")[3].split("_")[0] for i in ocr22["video_clip_path"]])
endtime.append([(i).split("/")[3].split("_")[1] for i in ocr22["video_clip_path"]])
start = pd.Series(data = starttime[0], index = range(0, len(starttime[0])))
end = pd.Series(data = starttime[0], index = range(0, len(starttime[0])))
ocr22["start"] = pd.to_datetime(start, format='%Y%m%d%H%M%S%f')
ocr22["end"] = pd.to_datetime(end, format='%Y%m%d%H%M%S%f')
ocr22.sort_values("start", inplace = True)
ocr22 = ocr22.reset_index()
ocr22["weight_timestart"] = pd.to_datetime(ocr22["start"]).astype(int) / 10**9
ocr22["weight_timeend"] = pd.to_datetime(ocr22["end"]).astype(int) / 10**9

event_temp_name = []
event_temp_name.append(["ocr-" + str(i) for i in range(0, len(ocr22))])
ocr22["event_temp_name"] = event_temp_name[0]

# Weights
weights22 = pd.read_csv("data/weight_loggs_all_2022_split_events.csv")
weights22 = weights22[weights22["scale"] == "toms"]
weights22.sort_values("event_timestamp_begin", inplace = True)

event_temp_name = []
event_temp_name.append(["weight-" + str(i) for i in range(0, len(weights22))])
weights22["event_temp_name"] = event_temp_name[0]

mindist = []
mindist_name = []
for ocr_event in ocr22.index: 
    ocr = ocr22.iloc[ocr_event]
    dist_start = weights22["event_timestamp_begin"] - ocr["weight_timestart"]
    nearest = weights22.iloc[np.argmin(abs(dist_start))]["event_temp_name"]
    mindist_name.append(nearest)
    mindist.append(min(abs(dist_start)))



# Combine data 
ocr22["weight_event"] = mindist_name
ocr22["dist_ocr_weight"] = mindist

combined = pd.merge(ocr22, weights22, left_on = "weight_event", right_on = "event_temp_name", how = "inner")
combined["ring"] = combined["str1"]+combined["str2"]
combined["ring"].value_counts()
combined["weight_mean"] = combined["event_mean"]-combined["bias_mean"]
combined["weight_median"] = combined["event_median"]-combined["bias_median"]

combined.to_csv("temp/combined_toms.csv", decimal = ",", sep = ";")


# Weight raw 2022
raw22 = pickle.load(open("data/weight_loggs_all_2022.pkl", "rb"))


b1 = combined[combined["ring"] == "ADG599"]
b2 = combined[combined["ring"] == "ADE034"]
b3 = combined[combined["ring"] == "ADE012"]
b4 = combined[combined["ring"] == "ACT778"]

fig, axs = plt.subplots(4)
axs[0].hist(b1["weight_median"], bins = np.arange(.5, 1.1, .01))
axs[1].hist(b2["weight_median"], bins = np.arange(.5, 1.1, .01))
axs[2].hist(b3["weight_median"], bins = np.arange(.5, 1.1, .01))
axs[3].hist(b4["weight_median"], bins = np.arange(.5, 1.1, .01))
plt.show()


#for i in ocr22.index:
#    ax.vlines(ocr22.iloc[i]["start"], 0, 10, color = "blue")
#    ax.vlines(ocr22.iloc[i]["end"], 0, 10, color = "red")

