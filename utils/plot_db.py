"""
Example: 
"""

import argparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sqlite3
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="Plot data from Auklab scale sqlit database")
    parser.add_argument(
        "--db_path",
        #default=Path("/home/bsp/git/ScaleDataAcquisition/back_output/20230429_dgt1.db"),
        default=Path("/home/bsp/git/ScaleDataAcquisition/back_output/20230429_dgt2.db"),
        type=Path,
        help="Data base path",
    )
    return parser.parse_args()

def load_db(db_path: Path):
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * from weights", con).sort_values(by=["timestamp"])
    con.close()

    return df


def plot_db(df: pd.DataFrame,db_path: Path):
    fig, ax = plt.subplots(4)
    fig.suptitle(db_path.name)
    #time = (df["timestamp"]-df["timestamp"].iloc[0])/1000.0

    #print(int(df["timestamp"].iloc[0]/1000.0))
    ts = pd.to_datetime(df["timestamp"].iloc[0], unit='ms')
    print(type(ts))

    print(ts)
    print(ts.date(), type(ts.date()))
    print(ts.time().strftime("%H:%M:%S"), type(ts.time()))

    ts = pd.to_datetime(df["timestamp"], unit='ms')
    print(ts.iloc[0].strftime("%H:%M:%S"))
    #time = ts.time().strftime("%H:%M:%S")
    time = [ti.strftime("%H:%M:%S") for ti in ts]
    
    for i in range(4):
        ax[i].plot(time,df[f"weight_{i}"])
        ax[i].set_title (f"cell {i}")
        ax[i].grid(True)
    plt.show()

def main() -> int:
    args = parse_args()
    df = load_db(args.db_path)
    plot_db(df,args.db_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
