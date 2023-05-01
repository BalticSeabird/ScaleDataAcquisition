"""
Example: command-line
./venv/bin/python weatherlinkdaq.py --request http://192.168.1.20/v1/current_conditions \
--output_root_path /home/erik/git/bsp/ScaleDataAcquisition/output/weatherlink \
--database_name weatherlink.db
"""

import argparse

from datetime import datetime
import logging
from multiprocessing import Process, Queue, Event
import numpy as np
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QObject
import queue
import requests
import sqlite3
import sys
import time


def _exit(logger: logging.Logger):
    logger.info(f"Exit")
    sys.exit(1)


def _init_logger(
    logger_root_path: Path, name: str, level=logging.INFO
) -> logging.Logger:
    if not logger_root_path.exists():
        logger_root_path.mkdir(parents=True, exist_ok=False)

    timestamp = time.strftime("%Y,%m,%d").replace(",", "")
    file_name = f"{timestamp}_{name}_log.txt"
    logger_path = logger_root_path.joinpath(file_name)

    logger = logging.getLogger(file_name)
    logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(logger_path, mode="a")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def parseargs():
    parser = argparse.ArgumentParser(description="Scale Data AcQuisition (DAQ)")
    parser.add_argument(
        "--request",
        default="http://192.168.1.20/v1/current_conditions",
        type=str,
        help="Weatherlink request",
    )
    module_path = Path(__file__).resolve().parent
    parser.add_argument(
        "--output_root_path",
        default=module_path.joinpath("weatherlink"),
        type=Path,
        help="Output root path",
    )
    parser.add_argument(
        "--database_name",
        default="weatherlink.db",
        type=str,
        help="Database name",
    )
    parser.add_argument(
        "--database_table",
        default="conditions",
        type=str,
        help="Database table",
    )
    # parser.add_argument(
    #     "--wait_for_connected",
    #     type=int,
    #     default=5000,
    #     help="Waits until the socket is connected, up to number of milliseconds",
    # )
    # parser.add_argument(
    #     "--wait_for_ready_read",
    #     type=int,
    #     default=5000,
    #     help="Waits until new data is available for reading,s up to number of milliseconds",
    # )
    return parser.parse_args()


def create(dp_path: Path, table: str, logger: logging.Logger):
    logger.info(f"Create database")
    try:
        connection = sqlite3.connect(dp_path)
        cursor = connection.cursor()
        sql = (
            f"create table if not exists {table} "
            "(timestamp integer not null primary key, "
            "tspc integer not null, "
            "temp real not null, "
            "hum real not null, "
            "dew_point real not null, "
            "wet_bulb real not null, "
            "wind_speed_last real not null, "
            "wind_dir_last integer not null, "
            "rain_size integer not null, "
            "rain_rate_last integer not null, "
            "rain_storm integer not null, "
            "solar_rad integer not null, "
            # "uv_index integer not null, "
            "rx_state integer not null)"
        )
        cursor.execute(sql)
        connection.commit()
        cursor.close()

    except sqlite3.Error as e:
        logger.error(f"Failed create sqlite database: {e}")
        _exit(logger)

    finally:
        if connection:
            connection.close()


def write2db(q: Queue, e: Event, db_path: Path, table: str):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    values = "(" + "?," * 12 + "?)"

    while not e.is_set():
        try:
            packet = q.get(timeout=1)
        except queue.Empty as ex:  # queue here refers to the module, not a class
            # print(f"Exception: {ex}")
            continue
        # print(packet)

        cursor.execute(
            f"insert or ignore into {table} values {values}",
            packet,
        )
        connection.commit()

    cursor.close()


class ReadScales(QObject):
    def __init__(self, *args, obj=None, **kwargs):
        super().__init__(obj)

        self.request = args[0].request
        self.output_root_path = args[0].output_root_path
        self.database_name = args[0].database_name
        self.database_table = args[0].database_table

        self.logger = args[1]

        if not self.output_root_path.exists():
            self.output_root_path.mkdir(parents=True, exist_ok=False)

        timestamp = time.strftime("%Y,%m,%d").replace(",", "")
        db_name = f"{timestamp}_{self.database_name}"
        db_path = self.output_root_path.joinpath(db_name)
        create(db_path, self.database_table, self.logger)

        self.queue = Queue()
        self.event = Event()
        self.process = Process(
            target=write2db,
            args=(
                self.queue,
                self.event,
                db_path,
                self.database_table,
            ),
        )
        self.process.start()

        on_fail_sleep_time = 5
        sleep_time = on_fail_sleep_time

        try:
            logger.info(f"Reading...")
            while True:
                r = requests.get("http://192.168.1.20/v1/current_conditions")
                status_code = r.status_code

                if status_code == 200:
                    sleep_time = on_fail_sleep_time
                    rd = r.json()
                    ts = rd["data"]["ts"]
                    tspc = int(time.time())  # pc timestamp
                    conditions = rd["data"]["conditions"][0]
                    self.queue.put(
                        [
                            ts,
                            tspc,
                            conditions["temp"],
                            conditions["hum"],
                            conditions["dew_point"],
                            conditions["wet_bulb"],
                            conditions["wind_speed_last"],
                            conditions["wind_dir_last"],
                            conditions["rain_size"],
                            conditions["rain_rate_last"],
                            conditions["rain_storm"],
                            conditions["solar_rad"],
                            # conditions["uv_index"],
                            conditions["rx_state"],
                        ]
                    )
                    time.sleep(5)
                else:
                    logger.error(
                        f"Failed to request: status: {status_code}, wait {sleep_time} seconds..."
                    )
                    sleep_time *= 2
                    sleep_time = np.clip(sleep_time, on_fail_sleep_time, 3600)
                    time.sleep(sleep_time)  # Perhaps wait longer

        except KeyboardInterrupt as e:
            print("interrupted!")
            self.logger.info("Keyboard interrupt (SIGINT) received")

        self.event.set()
        self.process.join()
        app.quit()

    # def error_occurred(self):
    #     logger.error(
    #         f"Error: {self.tcp_socket.error()}, {self.tcp_socket.errorString()}"
    #     )

    # def host_found(self):
    #     logger.info(f"Has found connection: state: {self.tcp_socket.state()}")

    # def connected(self):
    #     logger.info(f"Connected: state: {self.tcp_socket.state()}")


if __name__ == "__main__":
    args = parseargs()

    logger = _init_logger(
        logger_root_path=args.output_root_path.joinpath("log"),
        name=args.database_name.split(".")[0],
    )

    app = QCoreApplication(sys.argv)
    consol = ReadScales(args, logger)

    _exit(logger)
