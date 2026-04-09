"""
Efficient event category visualization
Processes categories and plots examples with minimal overhead
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("Waiting for step2 to complete weight calculations...")
print("(This script will run once step2_calculate_weight_stats.py finishes)\n")

# Create output directory
Path('out/event_examples').mkdir(exist_ok=True, parents=True)

def load_weight_db():
    """Load events from weights database"""
    db_path = Path('out/Events23-25_weights.db')
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query('SELECT * FROM event', con)
        con.close()
        return df
    except:
        con.close()
        return None

# Wait for weights DB to be populated
attempts = 0
max_attempts = 300  # 5 minutes max wait
all_events = None

while attempts < max_attempts:
    all_events = load_weight_db()

    if all_events is not None and len(all_events) > 100:
        print(f"✓ Weights database ready with {len(all_events)} events\n")
        break

    attempts += 1
    if attempts % 10 == 0:
        count = len(all_events) if all_events is not None else 0
        print(f"  Waiting for step2... ({count} events processed so far...)")

    import time
    time.sleep(1)

if all_events is None or len(all_events) == 0:
    print("✗ Timeout waiting for weights database")
    exit(1)

print("\n" + "="*80)
print("ANALYZING EVENT CATEGORIES FOR FAR3BONDEN3")
print("="*80 + "\n")

# Filter for FAR3BONDEN3 (DGT=dgt2, cell=1)
far3_events = all_events[(all_events['DGT'] == 'dgt2') & (all_events['cell'] == 1)].copy()
print(f"Total FAR3BONDEN3 events: {len(far3_events)}\n")

# Categorize
far3_events['category'] = 'other'
far3_events.loc[far3_events['weight_median'] > 0.75, 'category'] = 'good_heavy'
far3_events.loc[(far3_events['weight_median'] >= 0.05) & (far3_events['weight_median'] < 0.4), 'category'] = 'bad_light'
far3_events.loc[far3_events['weight_median'].isna(), 'category'] = 'missing'

print("Category Distribution:")
print(far3_events['category'].value_counts())
print()

# Process each category
categories = {
    'good_heavy': ('Good (weight > 0.75 kg)', 'Blues'),
    'bad_light': ('Bad (0.05-0.4 kg)', 'Oranges'),
    'missing': ('Missing/NaN', 'Reds')
}

for cat_key, (cat_label, _) in categories.items():
    cat_events = far3_events[far3_events['category'] == cat_key]

    if len(cat_events) == 0:
        print(f"⚠️  No events in category: {cat_label}")
        continue

    n_examples = min(50, len(cat_events))
    example_events = cat_events.sample(n=n_examples, random_state=42)

    print(f"\nCategory: {cat_label}")
    print(f"  Total in category: {len(cat_events)}")
    print(f"  Examples to visualize: {n_examples}")

    # Create summary for this category
    cat_dir = Path(f'out/event_examples/{cat_key}')
    cat_dir.mkdir(exist_ok=True, parents=True)

    # Write statistics
    with open(cat_dir / 'CATEGORY_STATS.txt', 'w') as f:
        f.write(f"Category: {cat_label}\n")
        f.write(f"Total events: {len(cat_events)}\n")
        f.write(f"Examples shown: {n_examples}\n\n")

        f.write("WEIGHT STATISTICS:\n")
        weights = cat_events['weight_median'].dropna()
        if len(weights) > 0:
            f.write(f"  Mean: {weights.mean():.4f} kg\n")
            f.write(f"  Median: {weights.median():.4f} kg\n")
            f.write(f"  Std: {weights.std():.4f} kg\n")
            f.write(f"  Min: {weights.min():.4f} kg\n")
            f.write(f"  Max: {weights.max():.4f} kg\n")
        f.write(f"  NaN count: {cat_events['weight_median'].isna().sum()}\n\n")

        f.write("DURATION STATISTICS:\n")
        durations = cat_events['Event_end'] - cat_events['Event_start']
        f.write(f"  Mean: {durations.mean() / 1000:.2f} seconds\n")
        f.write(f"  Median: {durations.median() / 1000:.2f} seconds\n")
        f.write(f"  Min: {durations.min() / 1000:.2f} seconds\n")
        f.write(f"  Max: {durations.max() / 1000:.2f} seconds\n\n")

        f.write("DATABASE FILES INVOLVED:\n")
        for db in cat_events['db_name'].unique():
            count = (cat_events['db_name'] == db).sum()
            f.write(f"  {db}: {count} events\n")

    # Create summary visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Weight distribution
    ax = axes[0, 0]
    weights_plot = cat_events['weight_median'].dropna()
    if len(weights_plot) > 0:
        ax.hist(weights_plot, bins=30, edgecolor='black', alpha=0.7, color='steelblue')
        ax.set_xlabel('Weight Median (kg)')
        ax.set_ylabel('Frequency')
        ax.set_title(f'Weight Distribution ({len(weights_plot)} events with data)')
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No weight data available', ha='center', va='center')

    # Plot 2: Event duration distribution
    ax = axes[0, 1]
    durations = (cat_events['Event_end'] - cat_events['Event_start']) / 1000  # convert to seconds
    ax.hist(durations, bins=30, edgecolor='black', alpha=0.7, color='coral')
    ax.set_xlabel('Duration (seconds)')
    ax.set_ylabel('Frequency')
    ax.set_title('Event Duration Distribution')
    ax.grid(True, alpha=0.3)

    # Plot 3: Weight vs Duration scatter
    ax = axes[1, 0]
    scatter_data = cat_events[cat_events['weight_median'].notna()].copy()
    if len(scatter_data) > 0:
        scatter_data['duration_s'] = (scatter_data['Event_end'] - scatter_data['Event_start']) / 1000
        ax.scatter(scatter_data['duration_s'], scatter_data['weight_median'],
                  alpha=0.6, s=50, color='darkgreen')
        ax.set_xlabel('Duration (seconds)')
        ax.set_ylabel('Weight Median (kg)')
        ax.set_title('Weight vs Event Duration')
        ax.grid(True, alpha=0.3)

    # Plot 4: Summary statistics text
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = (
        f"Category: {cat_label}\n\n"
        f"Total Events: {len(cat_events)}\n"
        f"Examples Visualized: {n_examples}\n\n"
    )

    weights_stats = cat_events['weight_median'].dropna()
    if len(weights_stats) > 0:
        summary_text += (
            f"Weight Stats (n={len(weights_stats)}):\n"
            f"  Mean: {weights_stats.mean():.3f} kg\n"
            f"  Median: {weights_stats.median():.3f} kg\n"
            f"  Range: {weights_stats.min():.3f} - {weights_stats.max():.3f} kg\n\n"
        )

    summary_text += (
        f"NaN Count: {cat_events['weight_median'].isna().sum()}\n\n"
        f"Duration Stats:\n"
        f"  Mean: {durations.mean():.2f} s\n"
        f"  Median: {durations.median():.2f} s\n"
        f"  Range: {durations.min():.2f} - {durations.max():.2f} s\n"
    )

    ax.text(0.1, 0.95, summary_text, transform=ax.transAxes,
           fontsize=10, verticalalignment='top', fontfamily='monospace',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(cat_dir / 'SUMMARY_STATISTICS.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    print(f"  ✓ Created summary plot: out/event_examples/{cat_key}/SUMMARY_STATISTICS.png")

print("\n" + "="*80)
print("SUMMARY STATISTICS COMPLETE")
print("="*80)
print("\nOutput created in:")
print("  out/event_examples/good_heavy/")
print("  out/event_examples/bad_light/")
print("  out/event_examples/missing/")
print("\nEach category contains:")
print("  - CATEGORY_STATS.txt (detailed statistics)")
print("  - SUMMARY_STATISTICS.png (visual summary charts)")
print("\n✓ Ready to generate individual event plots...")
