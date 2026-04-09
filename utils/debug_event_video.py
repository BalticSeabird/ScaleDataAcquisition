#!/usr/bin/env python3
"""Debug why event clips can become tiny or invalid files.

Usage example:
    python3 utils/debug_event_video.py --event-id BJORN3TRI3_SCALE_2023-05-09_16_05
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import pandas as pd
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from functions import create_connection  # noqa: E402


VID_PATHS = {
    "2023": Path("../../../../../../mnt/BSP_NAS2/Video/Video2023/"),
    "2024": Path("../../../../../../mnt/BSP_NAS2/Video/Video2024/"),
    "2025": Path("../../../../../../mnt/BSP_NAS2_vol4/Video/Video2025/"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug extraction for one event clip.")
    parser.add_argument(
        "--event-id",
        required=True,
        help="Event_ID from DB (with or without .mp4 suffix).",
    )
    parser.add_argument(
        "--db",
        default="out/Events23-25_weights.db",
        help="Path to sqlite DB containing table 'event'.",
    )
    parser.add_argument(
        "--output-dir",
        default="temp/debug_event_video",
        help="Directory where debug clips and logs are written.",
    )
    return parser.parse_args()


def normalize_event_id(event_id: str) -> str:
    return event_id[:-4] if event_id.lower().endswith(".mp4") else event_id


def fetch_event_row(db_path: Path, event_id: str) -> pd.Series:
    con = create_connection(str(db_path))
    if con is None:
        raise RuntimeError(f"Could not open database: {db_path}")

    try:
        query = "SELECT * FROM event WHERE Event_ID = ? LIMIT 1"
        df = pd.read_sql_query(query, con, params=(event_id,))
    finally:
        con.close()

    if df.empty:
        raise RuntimeError(f"Event_ID not found in DB: {event_id}")
    return df.iloc[0]


def resolve_source_video(row: pd.Series) -> tuple[Path, float, float, str]:
    date = pd.to_datetime(row["Day"])
    year = str(date.year)
    if year not in VID_PATHS:
        raise RuntimeError(f"Unsupported year {year} for event {row['Event_ID']}")

    datetext = date.strftime("%Y-%m-%d")
    camera = str(row["Cameraname"])
    video_name = str(row["Video_path"])

    sec_before = 5
    sec_after = 15 if year == "2023" else 5

    t1 = max(0.0, float(row["Sec_start"]) - sec_before)
    t2 = max(t1 + 1.0, float(row["Sec_end"]) + sec_after)

    video_path = VID_PATHS[year] / camera / datetext / video_name
    return video_path, t1, t2, year


def run_cmd(cmd: list[str], log_path: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if log_path is not None:
        log_path.write_text(
            "COMMAND:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + proc.stdout
            + "\n\nSTDERR:\n"
            + proc.stderr,
            encoding="utf-8",
        )
    return proc.returncode, proc.stdout, proc.stderr


def find_ffprobe(ffmpeg_exe: str) -> str:
    candidate = Path(ffmpeg_exe).with_name("ffprobe")
    return str(candidate) if candidate.exists() else "ffprobe"


def probe_video(ffprobe_exe: str, video_path: Path, label: str) -> dict | None:
    cmd = [
        ffprobe_exe,
        "-v",
        "error",
        "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,width,height,avg_frame_rate",
        "-of",
        "json",
        str(video_path),
    ]
    code, out, err = run_cmd(cmd)
    print(f"\n[{label}] ffprobe return code: {code}")
    if code != 0:
        print(f"[{label}] ffprobe error:\n{err.strip()}")
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        print(f"[{label}] ffprobe output was not valid JSON")
        return None

    duration = data.get("format", {}).get("duration", "unknown")
    size = data.get("format", {}).get("size", "unknown")
    print(f"[{label}] duration={duration} sec, size={size} bytes")
    return data


def print_file_stats(path: Path, label: str) -> None:
    if not path.exists():
        print(f"[{label}] missing output file: {path}")
        return
    stat = path.stat()
    print(f"[{label}] file exists, size={stat.st_size} bytes")


def main() -> int:
    args = parse_args()

    event_id = normalize_event_id(args.event_id)
    db_path = Path(args.db)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== Event Clip Debugger ===")
    print(f"Event ID: {event_id}")
    print(f"DB path:  {db_path.resolve()}")
    print(f"Output:   {output_dir.resolve()}")

    row = fetch_event_row(db_path, event_id)
    source_video, t1, t2, year = resolve_source_video(row)

    print("\n=== Event Metadata ===")
    print(f"Year:        {year}")
    print(f"Camera:      {row['Cameraname']}")
    print(f"Day:         {row['Day']}")
    print(f"Video file:  {row['Video_path']}")
    print(f"Sec_start:   {row['Sec_start']}")
    print(f"Sec_end:     {row['Sec_end']}")
    print(f"Clip window: {t1:.3f} -> {t2:.3f} (duration {t2 - t1:.3f} sec)")
    print(f"Source path: {source_video}")

    if not source_video.exists():
        print("\nERROR: source video does not exist.")
        return 2

    print_file_stats(source_video, "SOURCE")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe_exe = find_ffprobe(ffmpeg_exe)
    print(f"\nUsing ffmpeg:  {ffmpeg_exe}")
    print(f"Using ffprobe: {ffprobe_exe}")

    source_probe = probe_video(ffprobe_exe, source_video, "SOURCE")
    if source_probe is not None:
        duration_text = source_probe.get("format", {}).get("duration")
        try:
            source_duration = float(duration_text)
            if t1 >= source_duration:
                print(
                    "WARNING: clip start is outside source duration. "
                    "This can create tiny/invalid outputs."
                )
            if t2 > source_duration:
                print("WARNING: clip end is beyond source duration.")
        except (TypeError, ValueError):
            pass

    moviepy_out = output_dir / f"{event_id}_moviepy.mp4"
    copy_out = output_dir / f"{event_id}_copy.mp4"
    encode_out = output_dir / f"{event_id}_encode.mp4"

    print("\n=== Test 1: moviepy ffmpeg_extract_subclip (same method as script) ===")
    try:
        ffmpeg_extract_subclip(str(source_video), t1, t2, str(moviepy_out))
        print("moviepy extraction completed without exception")
    except Exception as exc:
        print(f"moviepy extraction failed: {exc}")
    print_file_stats(moviepy_out, "MOVIEPY")
    if moviepy_out.exists():
        probe_video(ffprobe_exe, moviepy_out, "MOVIEPY")

    print("\n=== Test 2: direct ffmpeg stream copy ===")
    copy_log = output_dir / f"{event_id}_copy_ffmpeg.log"
    copy_cmd = [
        ffmpeg_exe,
        "-y",
        "-ss",
        f"{t1:.3f}",
        "-to",
        f"{t2:.3f}",
        "-i",
        str(source_video),
        "-c",
        "copy",
        str(copy_out),
    ]
    copy_code, _, copy_err = run_cmd(copy_cmd, log_path=copy_log)
    print(f"ffmpeg copy return code: {copy_code}")
    if copy_code != 0:
        print("ffmpeg copy failed. See log for details.")
        print(copy_err.strip()[:1000])
    print_file_stats(copy_out, "COPY")
    if copy_out.exists():
        probe_video(ffprobe_exe, copy_out, "COPY")
    print(f"Copy log: {copy_log}")

    print("\n=== Test 3: direct ffmpeg re-encode (control test) ===")
    encode_log = output_dir / f"{event_id}_encode_ffmpeg.log"
    encode_cmd = [
        ffmpeg_exe,
        "-y",
        "-ss",
        f"{t1:.3f}",
        "-to",
        f"{t2:.3f}",
        "-i",
        str(source_video),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(encode_out),
    ]
    encode_code, _, encode_err = run_cmd(encode_cmd, log_path=encode_log)
    print(f"ffmpeg encode return code: {encode_code}")
    if encode_code != 0:
        print("ffmpeg encode failed. See log for details.")
        print(encode_err.strip()[:1000])
    print_file_stats(encode_out, "ENCODE")
    if encode_out.exists():
        probe_video(ffprobe_exe, encode_out, "ENCODE")
    print(f"Encode log: {encode_log}")

    print("\n=== Interpretation hints ===")
    print("- If SOURCE exists but MOVIEPY is tiny, moviepy extraction arguments may be problematic.")
    print("- If COPY is tiny/fails but ENCODE works, stream-copy around keyframes is likely the issue.")
    print("- If all outputs are tiny/fail, source file/path/time window is likely invalid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
