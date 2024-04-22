import datetime
import json
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import socket


def _init_logger(
    logger_root_path: Path, name: str, level=logging.INFO
) -> logging.Logger:
    timestamp = time.strftime("%Y,%m,%d").replace(",", "")
    file_name = f"{timestamp}_{name}_log.txt"
    logger_path = logger_root_path.joinpath(file_name)

    logger = logging.getLogger(file_name)
    logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    # file_handler = logging.FileHandler(logger_path, mode="a")
    file_handler = logging.FileHandler(logger_path, mode="w")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = _init_logger(
    logger_root_path=Path.cwd(),
    name="sample_weight_video_events",
)


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


def load_db(db_path: Path):
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * from events", con).sort_values(
        by=["timestamp_begin"]
    )
    con.close()

    return df


def build_ffmpeg_command(
    timestamp_begin_str: str,
    duration_str: str,
    input_video_path: Path,
    output_video_path: Path,
):
    input_video_path_str = str(input_video_path).replace(" ", "\ ")
    # alt -codec copy -map 0
    command = f"ffmpeg -ss {timestamp_begin_str} -i {input_video_path_str} -codec copy -t {duration_str} {str(output_video_path)}"
    ##command = f"ffmpeg -i {input_video_path_str} -ss {timestamp_begin_str}  -codec copy -t 00:20:00 {str(output_video_path)}"
    ##command = f"ffmpeg -i {input_video_path_str} -ss {timestamp_begin_str} -codec copy -t {duration_str} {str(output_video_path)}"

    return command


def run_ffmpeg(commands: list):
    try:
        cmd_stdout = subprocess.check_output(
            commands, stderr=subprocess.STDOUT, shell=True
        ).decode()
    except Exception as e:
        raise e


def make_weight_events_clips(
    db_path: Path,
    delta_time_min: datetime.timedelta,
    delta_time_max: datetime.timedelta,
    src_root_path: Path,
    dst_root_path: Path,
    n_samples: int,
    hostname: str,
):
    df = load_db(db_path)
    # df = df.sort_values(by=["timestamp_begin"])
    # df = df.sample(frac=1).reset_index(drop=True)
    df = df.sample(frac=1, random_state=1234).reset_index(drop=True)

    n_samples_count = 0

    for index, row in df.iterrows():
        try:
            time_start = datetime.datetime.fromtimestamp(row["timestamp_begin"] / 1000)
            time_end = datetime.datetime.fromtimestamp(row["timestamp_end"] / 1000)

            # Test same hour
            if time_start.hour != time_end.hour:
                # print("Weight event spans (begin and end) more than one hour")
                logger.info(f"Weight event spans (begin and end) more than one hour")
                continue

            # Filter size of segment
            delta_time = time_end - time_start
            if delta_time < delta_time_min or delta_time > delta_time_max:
                # print("Weight event is too long or too short.")
                logger.info(f"Weight event is too long or too short.")
                continue

            # Build video name
            date_start_str = time_start.date().strftime("%Y-%m-%d")

            # ddt fix
            if hostname == "frippe":
                if date_start_str != "2023-06-06":
                    continue

            delta_time_str_length = len(str(delta_time))
            if delta_time_str_length == 7 or delta_time_str_length == 8:
                delta_time_str = (
                    datetime.datetime.strptime(str(delta_time), "%H:%M:%S")
                    .time()
                    .strftime("%H:%M:%S")
                )
            else:
                delta_time_str = (
                    datetime.datetime.strptime(str(delta_time), "%H:%M:%S.%f")
                    .time()
                    .strftime("%H:%M:%S")
                )

            camera_name = db_path.stem.split("-")[0]

            video_datetime = datetime.datetime(
                time_start.year, time_start.month, time_start.day, hour=time_start.hour
            )
            video_time_str = video_datetime.time().strftime("%H.%M.%S")

            video_name = f"Auklab1_{camera_name}_{date_start_str}_{video_time_str}.mp4"
            video_root_path = src_root_path.joinpath(camera_name, date_start_str)
            video_path = video_root_path.joinpath(video_name)
            if not video_path.exists():
                # print(f"Video does not exists: {video_path}")
                logger.info(f"Video does not exists: {video_path}")
                continue

            video_path_str = str(video_path)
            out = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-show_format",
                    "-print_format",
                    "json",
                    video_path_str,
                ]
            )
            ffprobe_data = json.loads(out)
            duration_seconds = float(ffprobe_data["format"]["duration"])

            if duration_seconds < (3600 - 0.1):
                # print(f"Video duration is less than on hour: {video_path}")
                logger.info(f"Video duration is less than on hour: {video_path}")
                continue
            logger.info(f"Found: {video_path}")

            start_start_time = time_start - video_datetime

            start_start_time_str_length = len(str(start_start_time))
            if start_start_time_str_length == 7 or start_start_time_str_length == 8:
                start_start_time_str = (
                    datetime.datetime.strptime(str(start_start_time), "%H:%M:%S")
                    .time()
                    .strftime("%H:%M:%S")
                )
            else:
                start_start_time_str = (
                    datetime.datetime.strptime(str(start_start_time), "%H:%M:%S.%f")
                    .time()
                    .strftime("%H:%M:%S")
                )

            start_start_time_str_name = start_start_time_str.replace(":", ".")
            delta_time_str_name = delta_time_str.replace(":", ".")

            dst_video_name = (
                video_path.stem
#                + f"_{start_start_time_str_name}_{delta_time_str_name}.mp4"         # CHANGE HERE FOR EVENT NUM!
                + f"_{event}.mp4"
            )

            ffmpeg_cmnd = build_ffmpeg_command(
                timestamp_begin_str=start_start_time_str,
                duration_str=delta_time_str,
                input_video_path=video_path,
                output_video_path=dst_root_path.joinpath(dst_video_name),
            )

            logger.info(f"ffmpeg cmnd: {ffmpeg_cmnd}")

            run_ffmpeg(ffmpeg_cmnd)
        except Exception as e:
            logger.info(f"Exception: {e}")
            continue

        logger.info(f"Done: {dst_video_name}")

        n_samples_count += 1
        if n_samples_count >= n_samples:
            break
    logger.info(f"Done with {n_samples_count} samples of {n_samples}.")


def main() -> int:
    hostname = socket.gethostname()

    # System specific setting -quick fix
    if hostname == "frippe":
        src_root_path = Path("/mnt/xdisk/data/work/bsp/from_karlso")
        dst_root_path = Path.cwd().joinpath("ddt")
        db_root_path = Path("/home/erik/git/bsp/ScaleDataAcquisition/utils/output")
    elif hostname == "larus":
        src_root_path = Path("/home/bsp/mnt/nas1/BSP_data/BSP_data/Video/Video2023")
        dst_root_path = Path.cwd().joinpath("weight_event_clips_samples")
        db_root_path = Path.cwd().joinpath("db")
    elif hostname == "sprattus":
        src_root_path = Path("/home/bsp/mnt/nas1/BSP_data/BSP_data/Video/Video2023")    # Change
        dst_root_path = Path.cwd().joinpath("weight_event_clips_samples")               # Change
        db_root_path = Path.cwd().joinpath("db")                
    else:
        assert 0

    delta_time_min = datetime.timedelta(seconds=15)
    delta_time_max = datetime.timedelta(minutes=2)
    n_samples = 10

    remove_and_make_dir(dst_root_path, remove=True)

    logger.info(f"test logger {src_root_path}")
    logger.info(f"test logger {dst_root_path}")

    cameras = (
        "BJORN3TRI3_SCALE",
        "FAR3BONDEN3_SCALE",
        "FAR6BONDEN6_SCALE",
        "FAR6_SCALE",
        "TLZOOM",
        "FAR3_SCALE",
    )

    for cam in cameras:
        db_path = db_root_path.joinpath(f"{cam}-weight_events.db")
        dst_path = dst_root_path.joinpath(cam)
        if not dst_path.exists():
            dst_path.mkdir(parents=True, exist_ok=False)

        make_weight_events_clips(
            db_path=db_path,
            delta_time_min=delta_time_min,
            delta_time_max=delta_time_max,
            src_root_path=src_root_path,
            dst_root_path=dst_path,
            n_samples=n_samples,
            hostname=hostname,
        )

        sys.exit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
