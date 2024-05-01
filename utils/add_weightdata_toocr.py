
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
dbs1 = pd.DataFrame(data = d)


# Loop through cameras for 2023
rawpath = "/Volumes/JHS-SSD2/weightlogger/weight_logger/2023/backup/"

dx = {"scale": ["BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "FARBONDEN3_SCALE", "FAR6_SCALE", "FAR3_SCALE", "TLZOOM"],
    "dgt": ["dgt2", "dgt2", "dgt2", "dgt2", "dgt1", "dgt1"], 
    "cell": ["cell_2", "cell_3", "cell_1", "cell_4", "cell_4", "cell_3"]}
dbs2 = pd.DataFrame(data = dx)

# Loop through scales
for i in dbs1.index:
    t2name = "output/ocr/"+dbs1.iloc[i]["ocr_name"]
    t2 = df_from_db(t2name, "events", "number_of_detections>0", "number_of_detections>0", False)
    t2["ocr_datetime"] = pd.to_datetime(t2["weight_timestamp_begin"],unit='ms')
    
    path_save = "start"
    weight_median_new = []

    # Loop through ocr events 
    for j in t2.index:
        tempdat = t2.iloc[j:(j+1)]
        scale = tempdat["video_path"].iloc[0].split("/")[8]
        date = tempdat["video_path"].iloc[0].split("/")[9]  
        date2 = str(date).replace("-", "")
        if scale in ["BJORN3TRI3_SCALE", "FAR6BONDEN6_SCALE", "FAR3BONDEN3_SCALE", "FAR6_SCALE"]:
            dgt = "dgt2"
        else: 
            dgt = "dgt1"
        tempdat["scale"] = scale
        tempdat["dgt"] = dgt

        path = rawpath+date2+"/"+date2+"_"+dgt+".db"
        print(path)

        tempdat = pd.merge(tempdat, dbs2, on = ["scale", "dgt"], how = "left")
        cell = tempdat["cell"]
        start_i = tempdat["weight_idx_begin"][0]
        end_i = tempdat["weight_idx_end"][0]

        # Load data base        
        if path == path_save:
            pass # Do not load db again...
        else: 
            tempdb = df_from_db(path, "cells", "timestamp>0", "timestamp>0", True)
        
        if np.isnan(start_i):
            weight_mean_new.append(0)
            weight_median_new.append(0)
        else: 
            xx = tempdb.iloc[int(start_i):int(end_i)][cell]
            tare = tempdb.iloc[int(start_i)-55:int(start_i)-5][cell]
            tareweight = np.median(tare)
            median = np.median(xx)-tareweight
            weight_median_new.append(median)
        path_save = path
        
    # Save
    t2["weight_median2"] = weight_median_new
    insert_to_db(t2, "output/combined/weight_ocr_2023_new.db", "events")
