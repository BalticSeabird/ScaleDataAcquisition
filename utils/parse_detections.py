
import yaml
from pathlib import Path
import pandas as pd 


# Read yaml
def read_one_block_of_yaml_data(filename):
    with open(f'{filename}','r') as f:
        output = yaml.safe_load(f)
    return(output) 
    

# Define input path
path = Path("/mnt/xdisk/data/work/bsp/weight_events/2024/eval/")

yaml_files = path.rglob("*.yaml")

# Read all info from yaml
#test = Path("temp/Auklab1_BJORN3TRI3_SCALE_2024-06-24_21.00.00_1719256074_120_617.yaml")


# Empty df
d = {"ring": [], 
    "image": [], 
    "frame": []}
df = pd.DataFrame(d)

t = {"ring": [], 
    "number_of_detections": [], 
    "video": []}
tf = pd.DataFrame(t)


counter = 0
for file in yaml_files:

    obj = read_one_block_of_yaml_data(file)

    if "tag" in obj: 
    
        # Save objects 
        ring = obj["tag"]["str1"]+obj["tag"]["str2"]
        im = file.stem
        frame = obj["image_idx"]

        # create df
        d2 = {"ring": [ring], 
            "image": [im], 
            "frame": [frame]}
        df = pd.concat([pd.DataFrame(d2), df]) 

    else: 

        # Save objects 
        ring = obj["str1"]+obj["str2"]
        video = file.stem
        number_of_detections = obj["number_of_detections"]

        # create df
        t2 = {"ring": [ring], 
            "video": [video], 
            "number_of_detections": [number_of_detections]}
        tf = pd.concat([pd.DataFrame(t2), tf]) 


# Save
tf.to_csv("temp/Rings1_eval24.csv")
df.to_csv("temp/Rings2_eval24.csv")
