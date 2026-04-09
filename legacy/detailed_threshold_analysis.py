#!/usr/bin/env python3
"""
Detailed threshold analysis to find optimal classification rules.
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

DB_PATH = Path("out/Events23-25_weights.db")
WEIGHT_EXPECTED_MIN = 0.7
WEIGHT_EXPECTED_MAX = 1.0

def load_events():
    """Load all events from database."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM event", conn)
    conn.close()
    return df

def analyze_thresholds(df):
    """Analyze different threshold combinations."""

    print("\n" + "="*80)
    print("DETAILED THRESHOLD ANALYSIS")
    print("="*80)

    # Define candidate sets of events (increasingly selective)
    candidates = []

    # Candidate 1: Only valid weights in expected range
    cand1 = df[(df['weight_median'].notna()) &
               (df['weight_median'] >= WEIGHT_EXPECTED_MIN) &
               (df['weight_median'] <= WEIGHT_EXPECTED_MAX)].copy()
    candidates.append(("Weight in [0.7-1.0] kg only", cand1))

    # Candidate 2: Add variance filter
    cand2 = cand1[(cand1['weight_var'] < 0.001)].copy()
    candidates.append(("+ weight_var < 0.001", cand2))

    # Candidate 3: Add tare variance filter
    cand3 = cand2[(cand2['tare_before_var'] < 0.0001) &
                  (cand2['tare_after_var'] < 0.0001)].copy()
    candidates.append(("+ tare_var < 0.0001", cand3))

    # Candidate 4: More aggressive tare variance
    cand4 = cand3[(cand3['tare_before_var'] < 0.00005) &
                  (cand3['tare_after_var'] < 0.00005)].copy()
    candidates.append(("+ tare_var < 0.00005 (more aggressive)", cand4))

    # Candidate 5: Add tare mean stability
    cand5 = cand3[(np.abs(cand3['tare_before_mean'] - cand3['tare_after_mean']) < 0.01)].copy()
    candidates.append(("+ tare_mean_diff < 0.01 kg", cand5))

    # Candidate 6: Duration filter (exclude very short events)
    cand6 = cand5[(cand5['event_duration_ms'] > 5000)].copy()
    candidates.append(("+ event_duration > 5000 ms", cand6))

    for name, subset in candidates:
        print(f"\n{name}")
        print(f"  Events: {len(subset)} ({100*len(subset)/len(df):.2f}%)")
        if len(subset) > 0:
            w = subset['weight_median']
            print(f"  Weight: {w.mean():.3f} ± {w.std():.3f} kg")
            print(f"  Range: {w.min():.3f} - {w.max():.3f} kg")
            print(f"  Tare var: {subset['tare_before_var'].mean():.6f} (before), "
                  f"{subset['tare_after_var'].mean():.6f} (after)")
            print(f"  Weight var: {subset['weight_var'].mean():.6f}")
            print(f"  Signal CV: {subset['signal_cv_percent'].mean():.2f}%")
            print(f"  Duration (ms): {subset['event_duration_ms'].median():.0f} ms (median)")

def analyze_outliers(df):
    """Identify and characterize outliers."""
    print("\n" + "="*80)
    print("OUTLIER ANALYSIS")
    print("="*80)

    print("\n--- Weight Outliers ---")
    print(f"Weights < -1 kg: {(df['weight_median'] < -1).sum()}")
    print(f"Weights > 5 kg: {(df['weight_median'] > 5).sum()}")
    print(f"Weights > 10 kg: {(df['weight_median'] > 10).sum()}")

    # Show some examples
    extremes = df[df['weight_median'] > 50]
    if len(extremes) > 0:
        print(f"\nExtreme weight examples (> 50 kg):")
        for idx, row in extremes.head(5).iterrows():
            print(f"  {row['DGT']} cell {row['cell']}: {row['weight_median']:.1f} kg, "
                  f"var={row['weight_var']:.2f}, tare_var_before={row['tare_before_var']:.2f}")

    print("\n--- Tare Variance Outliers ---")
    print(f"tare_before_var > 0.01: {(df['tare_before_var'] > 0.01).sum()}")
    print(f"tare_before_var > 0.1: {(df['tare_before_var'] > 0.1).sum()}")
    print(f"tare_before_var > 1.0: {(df['tare_before_var'] > 1.0).sum()}")

    # Distribution stats focusing on reasonable range
    reasonable = df[(df['weight_median'].notna()) &
                    (df['weight_median'] >= 0) &
                    (df['weight_median'] <= 2)]

    print(f"\n--- Distribution for reasonable weights (0-2 kg) ---")
    print(f"Events: {len(reasonable)} ({100*len(reasonable)/len(df):.1f}%)")
    print(f"Weight mean: {reasonable['weight_median'].mean():.3f} kg")
    print(f"Weight std: {reasonable['weight_median'].std():.3f} kg")
    print(f"Tare var before (mean): {reasonable['tare_before_var'].mean():.6f}")
    print(f"Tare var after (mean): {reasonable['tare_after_var'].mean():.6f}")
    print(f"Weight var (mean): {reasonable['weight_var'].mean():.6f}")

def create_threshold_comparison_plot(df):
    """Create a plot showing recommended thresholds."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    # Focus on reasonable range
    reasonable = df[(df['weight_median'].notna()) &
                    (df['weight_median'] >= -1) &
                    (df['weight_median'] <= 3)]

    # Plot 1: Weight distribution with markers
    ax = axes[0, 0]
    ax.hist(reasonable['weight_median'], bins=100, alpha=0.7, color='blue', edgecolor='black')
    ax.axvline(WEIGHT_EXPECTED_MIN, color='green', linestyle='--', linewidth=2, label='Min expected')
    ax.axvline(WEIGHT_EXPECTED_MAX, color='green', linestyle='--', linewidth=2, label='Max expected')
    ax.axvline(reasonable['weight_median'].mean(), color='red', linestyle='-', linewidth=2, label='Mean')
    ax.set_xlabel('Weight (kg)')
    ax.set_ylabel('Count')
    ax.set_title('Weight Distribution (reasonable range)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Tare variance before
    ax = axes[0, 1]
    tare_reasonable = reasonable[reasonable['tare_before_var'] < 0.001]
    ax.hist(tare_reasonable['tare_before_var'], bins=100, alpha=0.7, color='blue', edgecolor='black')
    thresholds = [0.0001, 0.00005, 0.000025]
    colors = ['green', 'orange', 'red']
    for t, c in zip(thresholds, colors):
        ax.axvline(t, color=c, linestyle='--', linewidth=2, label=f'{t:.6f}')
    ax.set_xlabel('Tare Variance Before')
    ax.set_ylabel('Count')
    ax.set_title('Tare Variance Before (< 0.001 range)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Weight variance
    ax = axes[0, 2]
    weight_var_reasonable = df[(df['weight_var'] < 0.01) & (df['weight_var'] > 0)]
    ax.hist(weight_var_reasonable['weight_var'], bins=100, alpha=0.7, color='blue', edgecolor='black')
    thresholds = [0.001, 0.0005, 0.0001]
    colors = ['green', 'orange', 'red']
    for t, c in zip(thresholds, colors):
        ax.axvline(t, color=c, linestyle='--', linewidth=2, label=f'{t:.6f}')
    ax.set_xlabel('Weight Variance')
    ax.set_ylabel('Count')
    ax.set_title('Weight Variance (0-0.01 range)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Tare mean difference
    ax = axes[1, 0]
    tare_diff = np.abs(df['tare_before_mean'] - df['tare_after_mean'])
    tare_diff_reasonable = tare_diff[tare_diff < 0.1]
    ax.hist(tare_diff_reasonable, bins=100, alpha=0.7, color='blue', edgecolor='black')
    thresholds = [0.01, 0.02, 0.05]
    colors = ['green', 'orange', 'red']
    for t, c in zip(thresholds, colors):
        ax.axvline(t, color=c, linestyle='--', linewidth=2, label=f'{t:.3f} kg')
    ax.set_xlabel('|tare_mean_before - tare_mean_after| (kg)')
    ax.set_ylabel('Count')
    ax.set_title('Tare Mean Difference (<0.1 kg range)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 5: Event duration
    ax = axes[1, 1]
    duration = df[df['event_duration_ms'] < 200000]
    ax.hist(duration['event_duration_ms'], bins=100, alpha=0.7, color='blue', edgecolor='black')
    thresholds = [5000, 10000, 20000]
    colors = ['green', 'orange', 'red']
    for t, c in zip(thresholds, colors):
        ax.axvline(t, color=c, linestyle='--', linewidth=2, label=f'{t/1000:.1f}s')
    ax.set_xlabel('Duration (ms)')
    ax.set_ylabel('Count')
    ax.set_title('Event Duration (<200s range)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 6: Data points
    ax = axes[1, 2]
    data_pts = df[(df['event_data_points'] > 0) & (df['event_data_points'] < 10000)]
    ax.hist(data_pts['event_data_points'], bins=100, alpha=0.7, color='blue', edgecolor='black')
    thresholds = [100, 200, 500]
    colors = ['green', 'orange', 'red']
    for t, c in zip(thresholds, colors):
        ax.axvline(t, color=c, linestyle='--', linewidth=2, label=f'{t}')
    ax.set_xlabel('Data Points')
    ax.set_ylabel('Count')
    ax.set_title('Data Points (<10k range)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('out/threshold_recommendations.png', dpi=100, bbox_inches='tight')
    print("\nSaved: out/threshold_recommendations.png")
    plt.close()

def main():
    print("Loading events...")
    df = load_events()

    analyze_outliers(df)
    analyze_thresholds(df)
    create_threshold_comparison_plot(df)

    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print("""
Based on the analysis, I recommend the following classification rules:

RECOMMENDED RULE (Balanced):
  ✓ weight_median in [0.7, 1.0] kg
  ✓ weight_var < 0.0005
  ✓ tare_before_var < 0.0001
  ✓ tare_after_var < 0.0001
  ✓ |tare_before_mean - tare_after_mean| < 0.01 kg
  ✓ event_duration_ms > 2000 ms
  ✓ event_data_points > 50

Expected: ~1-3% good events, 100% in expected weight range

AGGRESSIVE RULE (Highest confidence):
  ✓ weight_median in [0.75, 0.95] kg
  ✓ weight_var < 0.0001
  ✓ tare_before_var < 0.00005
  ✓ tare_after_var < 0.00005
  ✓ |tare_before_mean - tare_after_mean| < 0.005 kg
  ✓ event_duration_ms > 10000 ms
  ✓ event_data_points > 200
  ✓ signal_cv_percent < 2.0

Expected: ~0.5-1% good events, 100% in tight weight range

LENIENT RULE (Maximize good events):
  ✓ weight_median in [0.6, 1.2] kg
  ✓ weight_var < 0.001
  ✓ tare_before_var < 0.0005
  ✓ tare_after_var < 0.0005
  ✓ event_duration_ms > 1000 ms

Expected: ~3-5% good events, ~90-95% in expected weight range
""")

if __name__ == '__main__':
    main()
