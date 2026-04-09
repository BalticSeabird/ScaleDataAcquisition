
# Goal: 
# Check 100 OCR videos - how many were correct?
# Check 100 videos that the OCR missed - how many were readable by humans?

from numpy.random import random
import pandas as pd
from functions import df_from_db, create_connection, insert_to_db
from pathlib import Path
import os

# Read full database of events (SQLite database)
events = df_from_db("out/Events23-25_weights.db", "event", "Event_start>0", "Sec_start>0.1", False)

# Remove Bonden1 station from events
events = events[events["Cameraname"] != "BONDEN1"]

# Read OCR rings
ocr = pd.read_csv("out/Rings1_all24.csv")

# Add OCR rings to events based on Event_ID
events = events.merge(ocr[["video", "ring"]], on="Event_ID")

# Sample 100 random rows of events with OCR rings
sample_with_ocr = events.dropna(subset=["Ring"]).sample(n=100, random_state=42)

# Sample 100 random rows of events without OCR rings                                                        
sample_without_ocr = events[events["Ring"].isna()].sample(n=100, random_state=42)

# Copy those event videos to a separate folder on the NAS

