"""
Example: command-line
./venv/bin/python scaledaq.py --host 192.168.1.205 \
--port 26 \
--no_scales 4 \
--output_root_path /home/erik/git/bsp/ScaleDataAcquisition/output \
--database_name 2023_scales_group_a.db

#--output_root_path /home/erik/git/pingo/sbsp/scale/output \
"""

import argparse
from dataclasses import dataclass, asdict
import logging
from multiprocessing import Process, Queue, Event
from pathlib import Path
from PySide6.QtCore import QByteArray, QCoreApplication, QIODeviceBase, QObject
from PySide6.QtNetwork import QTcpSocket
import queue
import sqlite3
import sys
import time


# From the manual Technical_Manual_DGT_V2_ENG.pdf
@dataclass(frozen=True)
class DGT_MultiScaleStringHH:
    ST: str = "Stability of the display"
    US: str = "Instability of the display"
    VL: str = "Value in microvolts relative to the weight"
    RZ: str = "Value in converter points relative to the weight"


@dataclass(frozen=True)
class DGT_SerialCharacters:
    CR: str = "\r"
    LF: str = "\n"


def _exit(logger: logging.Logger):
    logger.info(f"Exit")
    sys.exit(1)


def _init_logger(logger_root_path: Path, level=logging.INFO) -> logging.Logger:
    if not logger_root_path.exists():
        logger_root_path.mkdir(parents=True, exist_ok=False)

    timestamp = time.strftime("%Y,%m,%d").replace(",", "")
    file_name = f"{timestamp}_log.txt"
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
        "--host",
        default="192.168.1.205",
        type=str,
        help="Host ip address",
    )
    parser.add_argument(
        "--port",
        default=26,
        type=int,
        help="Port",
    )
    parser.add_argument(
        "--no_scales",
        type=int,
        default=4,
        metavar="N",
        help="Number of scales",
    )
    module_path = Path(__file__).resolve().parent
    parser.add_argument(
        "--output_root_path",
        default=module_path.joinpath("output"),
        type=Path,
        help="Output root path",
    )
    parser.add_argument(
        "--database_name",
        default="weights.db",
        type=str,
        help="Database name",
    )
    parser.add_argument(
        "--database_table",
        default="weights",
        type=str,
        help="Database table",
    )
    parser.add_argument(
        "--wait_for_connected",
        type=int,
        default=5000,
        help="Waits until the socket is connected, up to number of milliseconds",
    )
    parser.add_argument(
        "--wait_for_ready_read",
        type=int,
        default=5000,
        help="Waits until new data is available for reading,s up to number of milliseconds",
    )
    return parser.parse_args()


def create(dp_path: Path, table: str, no_scales: int, logger: logging.Logger):
    logger.info(f"Create database")
    try:
        connection = sqlite3.connect(dp_path)
        cursor = connection.cursor()
        sql = (
            f"create table if not exists {table} "
            "(timestamp integer primary key not null, "
        )
        for i in range(no_scales - 1):
            sql += f"weight_{i} real not null, "
        sql += f"weight_{no_scales-1} real not null)"
        cursor.execute(sql)
        connection.commit()
        cursor.close()

    except sqlite3.Error as e:
        logger.error(f"Failed create sqlite database: {e}")
        _exit(logger)

    finally:
        if connection:
            connection.close()


def write2db(q: Queue, e: Event, db_path: Path, table: str, no_scales: int):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    values = "(" + "?," * no_scales + "?)"

    while not e.is_set():
        try:
            packet = q.get(timeout=1)
        except queue.Empty as ex:  # queue here refers to the module, not a class
            # print(f"Exception: {ex}")
            continue
        packet_split = packet.split(",")
        timestamp = int(packet_split[-1])
        sample = [timestamp]
        for i in range(no_scales):
            sample.append(float(packet_split[1 + i * 3]))

        cursor.execute(
            f"insert or ignore into {table} values {values}",
            sample,
        )
        connection.commit()

    cursor.close()


class ReadScales(QObject):
    _terminator_characters = DGT_SerialCharacters.CR + DGT_SerialCharacters.LF
    _length_reading = 15

    def __init__(self, *args, obj=None, **kwargs):
        super().__init__(obj)

        self.host = args[0].host
        self.port = args[0].port
        self.no_scales = args[0].no_scales
        self.output_root_path = args[0].output_root_path
        self.database_name = args[0].database_name
        self.database_table = args[0].database_table
        self.wait_for_connected = args[0].wait_for_connected
        self.wait_for_ready_read = args[0].wait_for_ready_read

        self.logger = args[1]

        self.data = QByteArray()
        self.tcp_socket = QTcpSocket()
        self.multi_scale_string_hh = asdict(DGT_MultiScaleStringHH())

        self.length_packet = self._length_reading * self.no_scales + 1

        if not self.output_root_path.exists():
            self.output_root_path.mkdir(parents=True, exist_ok=False)

        timestamp = time.strftime("%Y,%m,%d").replace(",", "")
        db_name = f"{timestamp}_{self.database_name}.txt"
        db_path = self.output_root_path.joinpath(db_name)
        create(db_path, self.database_table, self.no_scales, self.logger)

        self.tcp_socket.errorOccurred.connect(self.error_occurred)
        self.tcp_socket.hostFound.connect(self.host_found)
        self.tcp_socket.connected.connect(self.connected)

        self.tcp_socket.connectToHost(
            self.host,
            self.port,
            QIODeviceBase.ReadOnly,
        )

        self.queue = Queue()
        self.event = Event()
        self.process = Process(
            target=write2db,
            args=(
                self.queue,
                self.event,
                db_path,
                self.database_table,
                self.no_scales,
            ),
        )
        self.process.start()

        try:
            if self.tcp_socket.waitForConnected(self.wait_for_connected):
                self.sync_data_stream()

                logger.info(f"Reading...")

                while self.tcp_socket.waitForReadyRead(self.wait_for_connected):
                    self.data.append(self.tcp_socket.readAll())
                    while self.data.length() >= self.length_packet:
                        packet = (
                            self.data.mid(0, self.length_packet)
                            .data()
                            .decode()
                            .replace(self._terminator_characters, "")
                        )
                        timestamp = str(int(1000 * time.time()))  # milliseconds

                        packet_split = packet.split(",")
                        if packet_split[0] in self.multi_scale_string_hh:
                            self.queue.put(packet + f",{timestamp}")
                            self.data = self.data.last(
                                self.data.size() - self.length_packet
                            )
                        else:
                            logger.info(f"Running: out of sync, reset...")
                            self.data.clear()

        except KeyboardInterrupt as e:
            self.logger.info("Keyboard interrupt (SIGINT) received")

        if self.tcp_socket.state() != QTcpSocket.SocketState.ConnectedState:
            logger.error(f"Failed to connect: state: {self.tcp_socket.state()}")

        self.event.set()
        self.process.join()
        app.quit()

    def sync_data_stream(self):
        logger.info(f"Sync data stream...")
        n_tries = 1000
        c_tries = 0
        while self.tcp_socket.waitForReadyRead(self.wait_for_ready_read):
            packet = self.tcp_socket.readAll()
            packet_split = (
                packet.data()
                .decode()
                .replace(self._terminator_characters, "")
                .split(",")
            )
            if (
                len(packet) == self.length_packet
                and packet_split[0] in self.multi_scale_string_hh
            ):
                self.data.append(packet)
                break
            else:
                c_tries += 1
                if c_tries > n_tries:
                    logger.error(
                        f"Failed to sync data stream, number of tries: {n_tries}"
                    )
                    _exit(logger)
                else:
                    logger.info(f"Out of sync try again...")

    def error_occurred(self):
        logger.error(
            f"Error: {self.tcp_socket.error()}, {self.tcp_socket.errorString()}"
        )

    def host_found(self):
        logger.info(f"Has found connection: state: {self.tcp_socket.state()}")

    def connected(self):
        logger.info(f"Connected: state: {self.tcp_socket.state()}")


if __name__ == "__main__":
    args = parseargs()

    logger = _init_logger(logger_root_path=args.output_root_path.joinpath("log"))

    app = QCoreApplication(sys.argv)

    consol = ReadScales(args, logger)

    _exit(logger)
