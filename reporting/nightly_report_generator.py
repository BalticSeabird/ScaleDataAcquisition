"""
Enhanced report generation for nightly monitoring
Generates comprehensive reports with file info, quality metrics per DGT, and explanations
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Optional


def generate_comprehensive_report(
    config: dict,
    df: pd.DataFrame,
    report_date: Optional[datetime] = None,
    file_info: Dict = None
) -> str:
    """Generate comprehensive report with all metrics, file info, and explanations"""

    if report_date is None:
        report_date = datetime.now()
    if file_info is None:
        file_info = {}

    quality_names = {1: "Excellent", 2: "Good", 3: "Fair", 4: "Poor"}
    lines = []

    # Header
    lines.append("=" * 90)
    lines.append(f"WEIGHT SENSOR DAILY REPORT - {report_date.strftime('%Y-%m-%d')}")
    lines.append("=" * 90)

    if df.empty:
        lines.append("\nNo events detected.")
        return "\n".join(lines)

    lines.append(f"\nReport Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Data Date: {report_date.strftime('%Y-%m-%d')}")

    # File Information Section
    lines.append("\n" + "-" * 90)
    lines.append("DATA FILES PROCESSED")
    lines.append("-" * 90)
    for db_name in sorted(df["db_name"].unique()):
        start_time, end_time = file_info.get(db_name, (None, None))
        line = f"{db_name}"
        if start_time and end_time:
            line += f"  |  {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}"
        lines.append(f"  {line}")

    # Overall Statistics
    lines.append("\n" + "-" * 90)
    lines.append("OVERALL STATISTICS")
    lines.append("-" * 90)
    lines.append(f"Total events detected: {len(df)}")

    events_with_weights = df[df["weight_median"].notna()]
    events_without_weights = df[df["weight_median"].isna()]

    if len(events_with_weights) > 0:
        lines.append(f"Events with valid weights: {len(events_with_weights)} "
                    f"({100*len(events_with_weights)/len(df):.1f}%)")
        lines.append(f"  Average weight: {events_with_weights['weight_median'].mean():.2f} kg")
        lines.append(f"  Weight range: {events_with_weights['weight_median'].min():.2f} - "
                    f"{events_with_weights['weight_median'].max():.2f} kg")

    if len(events_without_weights) > 0:
        lines.append(f"\nEvents without weight data: {len(events_without_weights)} "
                    f"({100*len(events_without_weights)/len(df):.1f}%)")
        lines.append("  Cause: Very brief events (<6 data points) or missing tare baseline")

    # Overall Quality Distribution
    if "quality_mark" in df.columns:
        lines.append("\nQuality Distribution (All Events):")
        for mark in [1, 2, 3, 4]:
            count = (df["quality_mark"] == mark).sum()
            if count > 0:
                pct = 100 * count / len(df)
                lines.append(f"  {quality_names[mark]:<12}: {count:>4} ({pct:>5.1f}%)")

    # Per-DGT Summary with Quality Breakdown
    lines.append("\n" + "-" * 90)
    lines.append("SUMMARY BY DGT AND CELL")
    lines.append("-" * 90)

    dgts = config["dgts"]
    cells_per_dgt = config["cells_per_dgt"]

    for dgt in dgts:
        dgt_data = df[df["DGT"] == dgt]
        if len(dgt_data) == 0:
            lines.append(f"\n{dgt}: No events")
            continue

        lines.append(f"\n{dgt}:")
        lines.append(f"  Total events: {len(dgt_data)}")

        # Quality distribution for this DGT
        lines.append(f"  Quality breakdown:")
        for mark in [1, 2, 3, 4]:
            count = (dgt_data["quality_mark"] == mark).sum()
            if count > 0:
                pct = 100 * count / len(dgt_data)
                lines.append(f"    {quality_names[mark]:<12}: {count:>3} ({pct:>5.1f}%)")

        # Per-cell details
        for cell in range(1, cells_per_dgt + 1):
            cell_data = dgt_data[dgt_data["cell"] == cell]
            if len(cell_data) == 0:
                continue

            event_count = len(cell_data)
            cell_weights = cell_data[cell_data["weight_median"].notna()]

            # Get scale name if available
            scale_name = ""
            if "Cameraname" in cell_data.columns and cell_data["Cameraname"].iloc[0]:
                scale_name = cell_data["Cameraname"].iloc[0]

            line = f"    Cell {cell}"
            if scale_name:
                line += f" ({scale_name})"
            line += f": {event_count} events"

            if len(cell_weights) > 0:
                avg_weight = cell_weights["weight_median"].mean()
                line += f" | Avg: {avg_weight:.2f} kg"

                if "quality_mark" in df.columns:
                    excellent = (cell_weights["quality_mark"] == 1).sum()
                    good = (cell_weights["quality_mark"] == 2).sum()
                    fair = (cell_weights["quality_mark"] == 3).sum()
                    poor = (cell_weights["quality_mark"] == 4).sum()
                    quality_str = f"Q: {excellent}E {good}G {fair}F {poor}P"
                    line += f" | {quality_str}"

            lines.append(line)

    # Sensor Health Check
    lines.append("\n" + "-" * 90)
    lines.append("SENSOR HEALTH CHECK")
    lines.append("-" * 90)

    issues = []

    if "tare_before_var" in df.columns and "tare_after_var" in df.columns:
        high_tare_var = (
            ((df["tare_before_var"] > 0.001) | (df["tare_after_var"] > 0.001)).sum()
        )
        if high_tare_var > 0:
            issues.append(f"⚠️  {high_tare_var} events with high baseline noise")

    if "weight_var" in df.columns:
        high_weight_var = (df["weight_var"] > 0.001).sum()
        if high_weight_var > 0:
            issues.append(f"⚠️  {high_weight_var} events with high signal noise")

    if issues:
        for issue in issues:
            lines.append(issue)
    else:
        lines.append("✓ All sensors functioning normally")

    lines.append("\n" + "=" * 90)

    return "\n".join(lines)
