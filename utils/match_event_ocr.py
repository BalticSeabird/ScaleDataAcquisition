
import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
import matplotlib.pyplot as plt

# For 2023 data

d = {"scale": ["BJORN3TRI3", "FAR6BONDEN6", "FARBONDEN3", "FAR6", "FAR3", "TLZOOM"],
    "ocr_name": ["BJORN3TRI3_SCALE_read_ring_tag.db", 
                "FAR6BONDEN6_SCALE_read_ring_tag.db",
                "FAR3BONDEN3_SCALE_read_ring_tag.db",
                "FAR6_SCALE_read_ring_tag.db",
                "FAR3_SCALE_read_ring_tag.db",
                "TLZOOM_read_ring_tag.db"], 
    "weights_name": ["BJORN3TRI3_SCALE-weight_events.db",
                "FAR6BONDEN6_SCALE-weight_events.db",
                "FAR3BONDEN3_SCALE-weight_events.db",
                "FAR6_SCALE-weight_events.db",
                "FAR3_SCALE-weight_events.db", 
                "TLZOOM-weight_events.db"]}
dbs = pd.DataFrame(data = d)


# Loop through cameras for 2023
for i in dbs.index:
    t1name = "output/ddt/"+dbs.iloc[i]["weights_name"]
    t1 = df_from_db(t1name, "events", "event_length>0", "event_length>0", True)
    t2name = "output/ocr/"+dbs.iloc[i]["ocr_name"]
    t2 = df_from_db(t2name, "events", "number_of_detections>0", "number_of_detections>0", False)
    t2["ocr_datetime"] = pd.to_datetime(t2["weight_timestamp_begin"],unit='ms')
    t3 = pd.merge(t1, t2, how = "outer", right_on = "weight_timestamp_begin", left_on = "timestamp_begin")
    insert_to_db(t3, "output/combined/weight_ocr_2023_v2.db", "events")


# Add missing weight data for those (of some reason...) missing in the original weight-database...
t1name = "output/combined/weight_ocr_2023_v2.db"
t1 = df_from_db(t1name, "events", "event_length>0", "event_length>0", True)
scale = []
date = []
dgt = []
for i in t1.index:
    if t1["video_path"].iloc[i] is None: 
        scale.append("none")
        date.append(0)
        dgt.append("none")
    else: 
        stat = t1["video_path"].iloc[i].split("/")[8]
        scale.append(stat)
        date.append(t1["video_path"].iloc[i].split("/")[9])    
        if stat in ["BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "FAR3BONDEN3_SCALE", "FAR6_SCALE"]:
            dgt.append("dgt2")
        else: 
            dgt.append("dgt1")

t1["dgt"] = dgt
t1["date"] = date
t1["scale"] = scale


# Find weight data for those missing 
dx = {"scale": ["BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "FARBONDEN3_SCALE", "FAR6_SCALE", "FAR3_SCALE", "TLZOOM"],
    "dgt": ["dgt2", "dgt2", "dgt2", "dgt2", "dgt1", "dgt1"], 
    "cell": ["cell_2", "cell_3", "cell_1", "cell_4", "cell_4", "cell_3"]}
dbs = pd.DataFrame(data = dx)

t1 = pd.merge(t1, dbs, on = ["scale", "dgt"], how = "left")

rawpath = raw = "/Volumes/JHS-SSD2/weightlogger/weight_logger/2023/backup/"

weight_mean_new = []
weight_median_new = []

for i in t1.index: 
    d = str(t1.iloc[i]["date"]).replace("-", "")
    if len(d) < 6:
        weight_mean_new.append(0)
        weight_median_new.append(0)    
    else:
        path = rawpath+d+"/"+d+"_"+t1.iloc[i]["dgt"]+".db"
        tempdb = df_from_db(path, "cells", "timestamp>0", "timestamp>0", True)
        cell = t1.iloc[i]["cell"]
        start_i = t1["weight_idx_begin_y"].iloc[i]
        end_i = t1["weight_idx_end_y"].iloc[i]
        if np.isnan(start_i):
            weight_mean_new.append(0)
            weight_median_new.append(0)
        else: 
            xx = tempdb.iloc[int(start_i):int(end_i)][cell]
            tare = tempdb.iloc[int(start_i)-55:int(start_i)-5][cell]
            tareweight = np.median(tare)
            median = np.median(xx)-tareweight
            mean = np.mean(xx)-tareweight
            print(t1.iloc[i]["video_clip_path"])
            print(median)
            weight_mean_new.append(mean)
            weight_median_new.append(median)
        

# Save
t1["weight_mean2"] = weight_mean_new
t1["weight_median2"] = weight_median_new
insert_to_db(t1, "output/combined/weight_ocr_2023_complemented.db", "events")
