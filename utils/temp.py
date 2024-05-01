


import pandas as pd
import numpy as np
from functions import df_from_db, create_connection, insert_to_db
import matplotlib.pyplot as plt


# Raw weights 
raw = "/Volumes/JHS-SSD2/weightlogger/weight_logger/2023/backup/20230520/20230520_dgt2.db"
rawd = df_from_db(raw, "cells", "timestamp>0", "timestamp>0", True)
fig, ax = plt.subplots()
ax.scatter(rawd["timestamp"], rawd["cell_4"])
plt.show()

# Database 
t2name = "output/ocr/FAR3BONDEN3_SCALE_read_ring_tag.db"
t2 = df_from_db(t2name, "events", "number_of_detections>0", "number_of_detections>0", False)
t2["start"] = pd.to_datetime(t2["weight_timestamp_begin"],unit='ms')

fig, ax = plt.subplots()
ax.scatter(t2["start"], t2["weight_timestamp_begin"])
plt.show()





# Check data 

# Merged db of weights
#fig, ax = plt.subplots()
#ax.scatter(t1["starttime"], t1["weight_mean"])
#ax.plot(t1["starttime"], t1["weight_mean"])
#plt.show()

# Raw weights 
raw = "/Volumes/JHS-SSD2/weightlogger/weight_logger/2023/backup/20230525/20230525_dgt2.db"
rawd = df_from_db(raw, "cells", "timestamp>0", "timestamp>0", True)
fig, ax = plt.subplots()
ax.scatter(rawd["timestamp"], rawd["cell_3"])
plt.show()

