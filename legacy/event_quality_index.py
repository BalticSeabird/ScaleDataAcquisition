"""
Create quality index for all events based on three classification rules.
Quality index: 1 = aggressive, 2 = moderate only, 3 = lenient only, 4 = none
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
import json

# Database path
DB_PATH = Path("out/Events23-25_weights.db")

def get_events_dataframe():
    """Load all events from database."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT
        Event_ID as event_id, Cameraname as station_id,
        weight_median, weight_var,
        tare_before_mean, tare_before_var,
        tare_after_mean, tare_after_var,
        event_duration_ms, event_data_points, signal_cv_percent
    FROM event
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    return df

def apply_quality_rules(df):
    """Apply all three rules and create quality index."""

    # AGGRESSIVE rule (quality 1)
    aggressive = (
        (df['weight_median'].notna()) &
        (df['weight_median'] >= 0.75) &
        (df['weight_median'] <= 0.95) &
        (df['weight_var'] < 0.0001) &
        (df['tare_before_var'] < 0.00005) &
        (df['tare_after_var'] < 0.00005) &
        (np.abs(df['tare_before_mean'] - df['tare_after_mean']) < 0.005) &
        (df['event_duration_ms'] > 10000) &
        (df['event_data_points'] > 200) &
        (df['signal_cv_percent'] < 2.0)
    )

    # MODERATE rule (quality 2 if not aggressive)
    moderate = (
        (df['weight_median'].notna()) &
        (df['weight_median'] >= 0.7) &
        (df['weight_median'] <= 1.0) &
        (df['weight_var'] < 0.0005) &
        (df['tare_before_var'] < 0.0001) &
        (df['tare_after_var'] < 0.0001) &
        (np.abs(df['tare_before_mean'] - df['tare_after_mean']) < 0.01) &
        (df['event_duration_ms'] > 2000) &
        (df['event_data_points'] > 50)
    )

    # LENIENT rule (quality 3 if not aggressive or moderate)
    lenient = (
        (df['weight_median'].notna()) &
        (df['weight_median'] >= 0.6) &
        (df['weight_median'] <= 1.2) &
        (df['weight_var'] < 0.001) &
        (df['tare_before_var'] < 0.0005) &
        (df['tare_after_var'] < 0.0005) &
        (df['event_duration_ms'] > 1000)
    )

    # Assign quality index
    quality_index = pd.Series(4, index=df.index)  # Default to 4 (none)
    quality_index[lenient] = 3
    quality_index[moderate] = 2
    quality_index[aggressive] = 1

    df['quality_index'] = quality_index
    df['passes_aggressive'] = aggressive
    df['passes_moderate'] = moderate
    df['passes_lenient'] = lenient

    return df

def get_station_stats(df):
    """Get summary statistics by station and quality index."""
    stats = defaultdict(lambda: defaultdict(int))

    for station_id in df['station_id'].unique():
        station_df = df[df['station_id'] == station_id]

        for qi in [1, 2, 3, 4]:
            count = (station_df['quality_index'] == qi).sum()
            stats[station_id][qi] = count

    return stats

def print_summary(df, stats):
    """Print summary statistics."""
    print("\n" + "="*80)
    print("QUALITY INDEX SUMMARY")
    print("="*80)
    print(f"\nTotal events: {len(df):,}")
    print(f"\nQuality index distribution (ALL DATA):")
    for qi in [1, 2, 3, 4]:
        count = (df['quality_index'] == qi).sum()
        pct = 100 * count / len(df)
        label = {1: "AGGRESSIVE", 2: "MODERATE only", 3: "LENIENT only", 4: "NONE"}[qi]
        print(f"  Q{qi} ({label:16s}): {count:7,} ({pct:5.1f}%)")

    print("\n" + "-"*80)
    print("PER-STATION BREAKDOWN")
    print("-"*80)
    print(f"{'Station':<15} {'Q1 Aggr.':<10} {'Q2 Mod.':<10} {'Q3 Len.':<10} {'Q4 None':<10} {'Total':<10}")
    print("-"*80)

    for station_id in sorted(stats.keys()):
        total = sum(stats[station_id].values())
        q1 = stats[station_id][1]
        q2 = stats[station_id][2]
        q3 = stats[station_id][3]
        q4 = stats[station_id][4]
        print(f"{station_id:<15} {q1:<10} {q2:<10} {q3:<10} {q4:<10} {total:<10}")

def plot_event_metrics_table(ax, event_info):
    """Create a text box with event metrics instead of timeseries (no raw data available)."""
    metrics_text = f"""
Event ID: {event_info['event_id']}

Weight: {event_info['weight_median']:.4f} kg
Var: {event_info['weight_var']:.6f}

Duration: {event_info['event_duration_ms']:.0f} ms
Data pts: {event_info['event_data_points']}

T_before_var: {event_info['tare_before_var']:.6f}
T_after_var: {event_info['tare_after_var']:.6f}

CV%: {event_info['signal_cv_percent']:.2f}%
"""
    ax.text(0.05, 0.95, metrics_text, transform=ax.transAxes,
           fontsize=7, verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

def plot_station_quality_samples(df, station_id, output_dir):
    """Create a figure with 10 sample events per quality category for a station."""
    station_df = df[df['station_id'] == station_id]
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(20, 12))
    fig.suptitle(f"Quality Index Samples - {station_id}", fontsize=16, fontweight='bold')

    plot_pos = 1

    for qi in [1, 2, 3, 4]:
        quality_df = station_df[station_df['quality_index'] == qi]
        label_map = {1: "Q1 Aggressive", 2: "Q2 Moderate", 3: "Q3 Lenient", 4: "Q4 None"}

        if len(quality_df) == 0:
            # Empty row for this quality category
            ax = plt.subplot(4, 10, plot_pos)
            ax.text(0.5, 0.5, f"{label_map[qi]}\n(No events)",
                   ha='center', va='center', fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
            plot_pos += 1
            for i in range(9):
                ax = plt.subplot(4, 10, plot_pos)
                ax.set_xticks([])
                ax.set_yticks([])
                plot_pos += 1
            continue

        # Sample up to 10 events
        sample_ids = quality_df['event_id'].sample(
            n=min(10, len(quality_df)), random_state=42
        ).values

        for idx, event_id in enumerate(sample_ids):
            event_info = quality_df[quality_df['event_id'] == event_id].iloc[0]

            ax = plt.subplot(4, 10, plot_pos)
            plot_pos += 1

            plot_event_metrics_table(ax, event_info)

    plt.tight_layout()
    output_file = outdir / f"quality_samples_{station_id}.png"
    plt.savefig(output_file, dpi=100, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()

def generate_quality_stats_json(df, stats):
    """Generate JSON summary of quality statistics."""
    summary = {
        "total_events": len(df),
        "quality_distribution": {
            "Q1_aggressive": int((df['quality_index'] == 1).sum()),
            "Q2_moderate_only": int((df['quality_index'] == 2).sum()),
            "Q3_lenient_only": int((df['quality_index'] == 3).sum()),
            "Q4_none": int((df['quality_index'] == 4).sum()),
        },
        "per_station": {}
    }

    for station_id in sorted(stats.keys()):
        summary["per_station"][station_id] = {
            "Q1_aggressive": int(stats[station_id][1]),
            "Q2_moderate_only": int(stats[station_id][2]),
            "Q3_lenient_only": int(stats[station_id][3]),
            "Q4_none": int(stats[station_id][4]),
            "total": int(sum(stats[station_id].values()))
        }

    return summary

def main():
    print("Loading events database...")
    df = get_events_dataframe()
    print(f"Loaded {len(df):,} events")

    print("Applying quality rules...")
    df = apply_quality_rules(df)

    print("Computing station statistics...")
    stats = get_station_stats(df)

    print_summary(df, stats)

    # Save quality-indexed database
    print("\nSaving quality indices to database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add quality columns to event table if they don't exist
    try:
        cursor.execute("ALTER TABLE event ADD COLUMN quality_index INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE event ADD COLUMN passes_aggressive BOOLEAN")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE event ADD COLUMN passes_moderate BOOLEAN")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE event ADD COLUMN passes_lenient BOOLEAN")
    except sqlite3.OperationalError:
        pass

    # Update quality data
    for _, row in df.iterrows():
        cursor.execute("""
        UPDATE event
        SET quality_index = ?, passes_aggressive = ?, passes_moderate = ?, passes_lenient = ?
        WHERE Event_ID = ?
        """, (
            int(row['quality_index']),
            bool(row['passes_aggressive']),
            bool(row['passes_moderate']),
            bool(row['passes_lenient']),
            row['event_id']
        ))

    conn.commit()
    conn.close()
    print("Quality index columns added to event table")

    # Generate JSON summary
    quality_summary = generate_quality_stats_json(df, stats)
    json_path = Path("out/quality_index_summary.json")
    with open(json_path, 'w') as f:
        json.dump(quality_summary, f, indent=2)
    print(f"\nJSON summary saved: {json_path}")

    # Generate plots for each station
    print("\nGenerating sample plots by station and quality index...")
    output_dir = Path("out/quality_samples")

    for station_id in sorted(df['station_id'].unique()):
        print(f"  {station_id}...", end='', flush=True)
        plot_station_quality_samples(df, station_id, output_dir)

    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"\nOutputs:")
    print(f"  - Database: quality_index columns added to event table in {DB_PATH}")
    print(f"  - Summary: {json_path}")
    print(f"  - Plots: {output_dir}")

if __name__ == "__main__":
    main()
