"""
Example: 
"""

from dataclasses import astuple, dataclass
import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

import ruptures as rpt
from sklearn.cluster import KMeans

from scipy.signal import savgol_filter
from scipy import stats
import shutil
import sqlite3
import sys

import random

# random.seed(1)

from datetime import datetime
import pytz


@dataclass(frozen=True)
class DGT1:
    CELL_1: str = "FAR8D_BOX"  # no cam
    CELL_2: str = "BONDEN1"  # no cam
    CELL_3: str = "TLZOOM"
    CELL_4: str = "FAR3_SCALE"


@dataclass(frozen=True)
class DGT2:
    CELL_1: str = "FAR3BONDEN3_SCALE"
    CELL_2: str = "BJORN3TRI3_SCALE"
    CELL_3: str = "FAR6BONDEN6_SCALE"
    CELL_4: str = "FAR6_SCALE"


@dataclass(frozen=True)
class DGT1_24:
    CELL_1: str = "FAR8D_BOX"  # no cam
    CELL_2: str = "BONDEN1"  # no cam
    CELL_3: str = "FAR6_SCALE"
    CELL_4: str = "FAR3_SCALE"


@dataclass(frozen=True)
class DGT2_24:
    CELL_1: str = "FAR3BONDEN3_SCALE"
    CELL_2: str = "BJORN3TRI3_SCALE"
    CELL_3: str = "FAR6BONDEN6_SCALE"
    CELL_4: str = "ROST2_SCALE"



#dgt_root_path = Path("/mnt/xdisk/data/work/bsp/auklab/weight_logger/")
#dgt_root_path = Path("data/")
dgt_root_path = Path("/Volumes/JHS-SSD2/weightlogger/weight_logger/2023/backup/")
files = dgt_root_path.glob("*.db")
# dst_root_path = Path.cwd().joinpath("output")
dst_root_path = Path.cwd().joinpath("output/ddt")

dgt1_names = astuple(DGT1())
dgt2_names = astuple(DGT2())

_do_plot = False
_do_plot_ddt = False


def remove_and_make_dir(dir_path: Path, remove: bool = False):
    if dir_path.exists() and remove:
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            print(f"Error: remove {str(dir_path)}, {e.strerror}")
            sys.exit(1)
    try:
        dir_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as e:
        print(f"Error: mkdir {str(dir_path)}, {e.strerror}")
        sys.exit(1)


def create(dp_path: Path, table: str):
    try:
        connection = sqlite3.connect(dp_path)
        cursor = connection.cursor()
        cursor.execute(
            (
                f"create table if not exists {table} "
                "(event str not null, "
                "timestamp_begin integer not null, "
                "timestamp_end integer not null, "
                "weight_idx_begin integer not null, "
                "weight_idx_end integer not null, " 
                "starttime str not null, "
                "event_length int not null, "
                "weight_mean float not null, " 
                "weight_mad float not null)"
            )
        )
        connection.commit()
        cursor.close()

    except sqlite3.Error as e:
        print(f"Failed creating sqlite data base: {e}")
        raise e

    finally:
        if connection:
            connection.close()


def write2db(db_path: Path, table: str, rows: list):
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        # cursor.execute("BEGIN TRANSACTION;")
        cursor.executemany(f"insert or ignore into {table} values (?,?,?,?,?,?,?,?,?)", rows)
        # cursor.execute("COMMIT;")
        connection.commit()
        cursor.close()

    except sqlite3.Error as e:
        print(f"Failed writing to sqlite data base: {e}")
        raise

    finally:
        if connection:
            connection.close()


def load_db(db_path: Path):
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])
    con.close()

    return df


def plot_db(df: pd.DataFrame, names: tuple):
    # print(f"plot {db_path.stem}")

    # time_start = datetime.fromtimestamp(
    #    df["timestamp"].iloc[0] / 1000, pytz.timezone("Europe/Stockholm")
    # )
    # time_end = datetime.fromtimestamp(
    #    df["timestamp"].iloc[-1] / 1000, pytz.timezone("Europe/Stockholm")
    # )
    # time_start = time_start.strftime("%y-%m-%d %H:%M:%S")
    # time_end = time_end.strftime("%y-%m-%d %H:%M:%S")

    fig, ax = plt.subplots(4, figsize=(16, 9), sharex=True)
    # fig.suptitle(f"{db_path.stem}: {time_start} to {time_end}")
    # fig.subplots_adjust(top=0.92)

    for i in range(0, 4):
        ax[i].plot(df[f"cell_{i+1}"])
        ax[i].set_title(f"cell {i+1}: {names[i]}")
        ax[i].grid(True)


def segment_weight_events(df: pd.DataFrame, names: tuple, date: str):
    if _do_plot:
        plot_db(df, names)

    # print(names)
    ##print(df.iloc[0])
    # sys.exit()

    for i in range(1, 5):
        for nc in range(2, 5):

            wl = df[f"cell_{i}"].to_numpy().reshape(-1, 1)
            kmeans = KMeans(
                n_clusters=nc,
                n_init="auto",
                random_state=1234,
            ).fit(wl)
            p = kmeans.predict(wl)
            s = kmeans.transform(wl)

            e = np.take_along_axis(s, p[:, None], axis=1)
            ies = np.argsort(e, axis=None)
            i_max = len(p) - int(len(p) * 1e-2)

            # if e[ies[i_max], 0] < 0.3:
            if e[ies[i_max], 0] < 0.6:
                break

            if _do_plot_ddt:
                fig, ax = plt.subplots(5, figsize=(16, 9), sharex=True)
                ax[0].plot(wl)
                ax[0].grid(True)
                ax[1].plot(p)
                ax[1].grid(True)
                for j in range(nc):
                    ax[2].plot(s[:, j])
                ax[2].grid(True)
                ax[3].plot(e)
                ax[3].grid(True)
                ax[4].plot(e[ies, 0])
                ax[4].plot(e[ies, 0], "*")
                ax[4].plot(i_max, e[ies[i_max], 0], "r*")
                ax[4].grid(True)
                plt.show()
                # sys.exit()

        wl = np.squeeze(wl)

        # # Tare weight
        cluster_centers_min_idx = np.argmin(kmeans.cluster_centers_)

        # print(kmeans.cluster_centers_)
        # print(cluster_centers_min_idx)
        # sys.exit()
        # p0 = np.where(p == cluster_centers_min_idx)[0]

        # zt = np.polyfit(p0, wl[p0], 1)
        # pt = np.poly1d(zt)
        # ii = np.arange(0, len(p))

        # n_plots = 3
        # fig, ax = plt.subplots(n_plots, figsize=(16, 9), sharex=True)
        # ax[0].plot(wl)
        # ax[1].plot(p)
        # ax[2].plot(p0, wl[p0])
        # ax[2].plot(ii, pt(ii))

        # for axi in range(n_plots):
        #     ax[axi].grid(True)

        # plt.show()

        dp = np.diff(p)
        assert isinstance(dp[0], np.int32)

        edge_idx = np.where(dp != 0)[0]
        de = np.diff(edge_idx, append=0, prepend=len(p) - 1)

        j_begin = 0
        count = 0
        segment_min_length = 100
        segments = []

        # print(kmeans.cluster_centers_)
        # print(np.diff(kmeans.cluster_centers_[:, 0]))
        if np.min(np.diff(kmeans.cluster_centers_[:, 0])) < 0.6:
            continue

        for j in edge_idx:
            j_end = j
            seg_weight_mean = np.mean(wl[j_begin:j_end])
            seg_weight_mad = stats.median_abs_deviation(wl[j_begin:j_end])
            if (
                j_end - j_begin > segment_min_length
                and seg_weight_mean - kmeans.cluster_centers_[0, 0] > 0.6
                and seg_weight_mad < 0.05
                # and p[int(0.5 * (j_end + j_begin))] != cluster_centers_min_idx
                # and stats.median_abs_deviation(wl[j_begin:j_end]) < 0.01
            ):
                # print(
                #     np.mean(wl[j_begin:j_end]),
                #     np.mean(wl[j_begin:j_end]) - kmeans.cluster_centers_[0, 0],
                #     # np.median(wl[(j_begin - 10) : j_begin]),
                #     # np.median(wl[j_end : (j_end + 10)]),
                #     stats.median_abs_deviation(wl[j_begin:j_end]),
                # )
                # segments.append(
                #     {
                #         "i_begin": i_begin,
                #         "i_end": i_end,
                #         "timestamp_begin": df.iloc[i_begin]["timestamp"],
                #         "timestamp_end": df.iloc[i_end]["timestamp"],
                #     }
                # )
                count += 1

                segments.append(
                    [
                        # int(df.iloc[j_begin]["timestamp"] / 1000),
                        # int(df.iloc[j_end]["timestamp"] / 1000),
                        names[i-1]+"-"+date + "-" + str(count),
                        int(df.iloc[j_begin]["timestamp"]),  # use msec
                        int(df.iloc[j_end]["timestamp"]),  # use msec
                        int(j_begin),
                        int(j_end),
                        pd.to_datetime(df.iloc[j_begin]["timestamp"],unit='ms').strftime('%Y-%m-%d %X'),
                        int(j_end-j_begin),
                        seg_weight_mean, 
                        seg_weight_mad, 
                    ]
                )
            j_begin = j

        # fig, ax = plt.subplots(2, figsize=(16, 9), sharex=True)
        # idx = np.arange(0, len(wl))
        # ax[0].set_title(names[i - 1])
        # for j in range(nc):
        #     ax[0].plot(idx, np.where(p == j, wl, None), label=str(j))
        # for seg in segments:
        #     seg_begin = seg[2]
        #     seg_end = seg[3]
        #     idx = np.arange(seg_begin, seg_end)
        #     ax[0].plot(idx, wl[idx], "r")
        #     ax[0].plot(seg_begin, wl[seg_begin], ">", color="gold")
        #     ax[0].plot(seg_end, wl[seg_end], "<", color="chartreuse")

        # ax[1].plot(p)

        # continue
        # break

        write2db(
            dst_root_path.joinpath(names[i - 1] + "-weight_events.db"),
            table="events",
            rows=segments,
        )
    # plt.show()
    # sys.exit()


def find_weight_events(root_path: Path):

    # db_path_list = [db_path for db_path in root_path.glob("**/*.db")]
    # for db_path in random.sample(db_path_list, 1):
    for db_path in root_path.rglob("*.db"):

        print(db_path)
        if "dgt2" in db_path.name:  
            names = dgt2_names
        else: 
            names = dgt1_names

        date = db_path.name.split("_")[0]

        df = load_db(db_path)
        df = df.sort_values(by=["timestamp"])

        segment_weight_events(df, names, date)

        # break


def main() -> int:
    remove_and_make_dir(dst_root_path, remove=True)

    for dgt in dgt1_names:
        create(dst_root_path.joinpath(dgt + "-weight_events.db"), "events")
    for dgt in dgt2_names:
        create(dst_root_path.joinpath(dgt + "-weight_events.db"), "events")

    find_weight_events(dgt_root_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())


