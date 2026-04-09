"""
Detailed event visualization: Pull 50 examples from each weight category
Shows the raw sensor data, tare windows, event window, and calculated weight
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Create output directory
Path('out/event_examples').mkdir(exist_ok=True)

def load_db(db_path, table):
    """Load database into dataframe"""
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f'SELECT * from {table}', con)
    except:
        df = None
        print(f'Error loading {db_path}')
    con.close()
    return df

def plot_event(event_row, data, event_num, category, station_name):
    """
    Plot a single event with:
    - Raw sensor data
    - Tare before window
    - Event window
    - Tare after window
    - Calculated weight
    """

    start = event_row['Event_start']
    end = event_row['Event_end']
    cell = int(event_row['cell'])
    weight_median = event_row['weight_median']

    # Parameters
    tare_length = 10000  # ms
    start_delay = 2000   # ms

    # Get windows
    tare_start = start - tare_length
    event_start_actual = start + start_delay
    event_end_actual = end - start_delay
    tare_end = end + tare_length

    # Extract data
    cond_full = (data['timestamp'] >= tare_start - 5000) & (data['timestamp'] <= tare_end + 5000)
    data_full = data[cond_full].copy()

    if len(data_full) == 0:
        return None

    # Get the column for this cell
    col = f'cell_{cell}'
    if col not in data_full.columns:
        return None

    # Prepare window colors
    colors = {
        'tare_before': data_full[(data_full['timestamp'] >= tare_start) & (data_full['timestamp'] <= start)],
        'event': data_full[(data_full['timestamp'] >= event_start_actual) & (data_full['timestamp'] <= event_end_actual)],
        'tare_after': data_full[(data_full['timestamp'] >= end) & (data_full['timestamp'] <= tare_end)]
    }

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot full data
    ax.plot(data_full['timestamp'], data_full[col], 'gray', alpha=0.3, linewidth=0.8, label='Full signal')

    # Highlight windows
    if len(colors['tare_before']) > 0:
        ax.scatter(colors['tare_before']['timestamp'], colors['tare_before'][col],
                  color='blue', alpha=0.6, s=10, label='Tare before (10s)')
    if len(colors['event']) > 0:
        ax.scatter(colors['event']['timestamp'], colors['event'][col],
                  color='red', alpha=0.8, s=20, label='Event window (no delays)')
    if len(colors['tare_after']) > 0:
        ax.scatter(colors['tare_after']['timestamp'], colors['tare_after'][col],
                  color='green', alpha=0.6, s=10, label='Tare after (10s)')

    # Add vertical lines for key times
    ax.axvline(start, color='black', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(end, color='black', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(event_start_actual, color='red', linestyle=':', alpha=0.7, linewidth=1)
    ax.axvline(event_end_actual, color='red', linestyle=':', alpha=0.7, linewidth=1)

    # Get statistics
    data_event = data[(data['timestamp'] > event_start_actual) & (data['timestamp'] < event_end_actual)][col]
    data_tare_before = data[(data['timestamp'] > tare_start) & (data['timestamp'] <= start)][col]
    data_tare_after = data[(data['timestamp'] >= end) & (data['timestamp'] < tare_end)][col]

    tare_med_before = data_tare_before.median()
    tare_med_after = data_tare_after.median()
    tare_avg = (tare_med_before + tare_med_after) / 2
    event_med = data_event.median() if len(data_event) > 0 else np.nan

    # Title and labels
    duration_s = (end - start) / 1000
    n_points = len(data_event)

    status = "✓ GOOD" if weight_median > 0.75 else ("✗ BAD" if (weight_median > 0 and weight_median < 0.5) else "? NaN")

    title = (f"{station_name} - Event #{event_num} ({category})\n"
             f"Duration: {duration_s:.1f}s | Data points in event: {n_points} | "
             f"Calculated weight: {weight_median:.3f} kg {status}")

    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('Timestamp (ms)', fontsize=10)
    ax.set_ylabel('Weight (kg)', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left', fontsize=9)

    # Add statistics box
    stats_text = (f"Event Raw Min: {data_event.min():.3f} kg\n"
                  f"Event Raw Max: {data_event.max():.3f} kg\n"
                  f"Event Raw Median: {event_med:.3f} kg\n"
                  f"Tare Before: {tare_med_before:.3f} kg\n"
                  f"Tare After: {tare_med_after:.3f} kg\n"
                  f"Tare Avg: {tare_avg:.3f} kg\n"
                  f"Weight (after tare): {weight_median:.3f} kg")

    ax.text(0.98, 0.97, stats_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    return fig

# Load events
print("Loading events database...")
events_db = Path('out/Events23-25_weights.db')
con = sqlite3.connect(events_db)
all_events = pd.read_sql_query('SELECT * FROM event', con)
con.close()

print(f"Total events in weights database: {len(all_events)}")

# Filter for FAR3BONDEN3 (DGT=dgt2, cell=1)
far3_events = all_events[(all_events['DGT'] == 'dgt2') & (all_events['cell'] == 1)].copy()
print(f"FAR3BONDEN3 events: {len(far3_events)}\n")

# Categorize events
far3_events['category'] = 'other'
far3_events.loc[far3_events['weight_median'] > 0.75, 'category'] = 'good_heavy'
far3_events.loc[(far3_events['weight_median'] >= 0.05) & (far3_events['weight_median'] <= 0.4), 'category'] = 'bad_light'
far3_events.loc[far3_events['weight_median'].isna(), 'category'] = 'missing'

print("Event Categories:")
print(far3_events['category'].value_counts())
print()

# Get 50 examples from each category
categories_to_plot = {
    'good_heavy': ('Good (0.8+ kg)', 'Seaborn-Blues'),
    'bad_light': ('Bad (0.05-0.4 kg)', 'Seaborn-Oranges'),
    'missing': ('Missing/NaN', 'Seaborn-Reds')
}

# Process each category
for cat_key, (cat_label, _) in categories_to_plot.items():
    cat_events = far3_events[far3_events['category'] == cat_key]

    if len(cat_events) == 0:
        print(f"⚠️  No events in category: {cat_label}")
        continue

    n_examples = min(50, len(cat_events))
    example_events = cat_events.sample(n=n_examples, random_state=42)

    print(f"Processing {n_examples} examples from: {cat_label}")

    # Create output directory
    cat_dir = Path(f'out/event_examples/{cat_key}')
    cat_dir.mkdir(exist_ok=True, parents=True)

    # Create summary stats
    summary_stats = {
        'category': cat_label,
        'total_count': len(cat_events),
        'examples_shown': n_examples,
        'weight_median_stats': {
            'mean': cat_events['weight_median'].mean(),
            'median': cat_events['weight_median'].median(),
            'std': cat_events['weight_median'].std(),
            'min': cat_events['weight_median'].min(),
            'max': cat_events['weight_median'].max(),
            'nan_count': cat_events['weight_median'].isna().sum()
        },
        'duration_stats': {
            'mean_seconds': (cat_events['Event_end'] - cat_events['Event_start']).mean() / 1000,
            'median_seconds': (cat_events['Event_end'] - cat_events['Event_start']).median() / 1000,
            'min_seconds': (cat_events['Event_end'] - cat_events['Event_start']).min() / 1000,
            'max_seconds': (cat_events['Event_end'] - cat_events['Event_start']).max() / 1000,
        }
    }

    with open(cat_dir / 'SUMMARY.txt', 'w') as f:
        f.write(f"Category: {cat_label}\n")
        f.write(f"Total events in this category: {summary_stats['total_count']}\n")
        f.write(f"Examples shown: {n_examples}\n\n")

        f.write("Weight Statistics:\n")
        for key, val in summary_stats['weight_median_stats'].items():
            f.write(f"  {key}: {val:.3f}" if not np.isnan(val) else f"  {key}: NaN\n")
            if not isinstance(val, float):
                f.write(f"\n")

        f.write("\nDuration Statistics:\n")
        for key, val in summary_stats['duration_stats'].items():
            f.write(f"  {key}: {val:.2f} seconds\n")

    # Plot each example
    success_count = 0
    for idx, (event_idx, event_row) in enumerate(example_events.iterrows()):
        db_name = event_row['db_name']

        # Find the raw data file
        db_file = list(Path('../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(db_name))

        if len(db_file) == 0:
            print(f"  ⚠️  Could not find raw data file: {db_name}")
            continue

        # Load raw data
        data = load_db(db_file[0], 'cells')
        if data is None or len(data) == 0:
            continue

        # Create plot
        fig = plot_event(event_row, data, idx + 1, cat_label, 'FAR3BONDEN3')

        if fig is None:
            continue

        # Save plot
        plt.savefig(cat_dir / f'event_{idx+1:03d}.png', dpi=100, bbox_inches='tight')
        plt.close(fig)

        success_count += 1

        if (idx + 1) % 10 == 0:
            print(f"  ✓ Plotted {idx + 1}/{n_examples} examples")

    print(f"  ✓ Successfully plotted {success_count}/{n_examples} examples\n")

print("\n" + "="*80)
print("VISUALIZATION COMPLETE")
print("="*80)
print("\nOutput locations:")
print("  - out/event_examples/good_heavy/     (50 examples of good weight data)")
print("  - out/event_examples/bad_light/      (50 examples of problematic data)")
print("  - out/event_examples/missing/        (50 examples of missing/NaN weights)")
print("\nEach directory contains:")
print("  - event_001.png through event_050.png (individual plots)")
print("  - SUMMARY.txt (statistics for the category)")
