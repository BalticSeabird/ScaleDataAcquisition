
import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db

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


for i in dbs.index:
    t1name = "output/ddt/"+dbs.iloc[i]["weights_name"]
    t1 = df_from_db(t1name, "events", "event_length>0", "event_length>0", True)
    t2name = "output/ocr/"+dbs.iloc[i]["ocr_name"]
    t2 = df_from_db(t2name, "events", "number_of_detections>0", "number_of_detections>0", False)
    t3 = pd.merge(t1, t2, how = "outer", right_on = "weight_timestamp_begin", left_on = "timestamp_begin")
    insert_to_db(t3, "output/combined/weight_ocr_2023.db", "events")

