#!/usr/bin/env python3
"""
Comprehensive event quality classification analysis.
Classifies events into good/bad based on data quality metrics.
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration
DB_PATH = Path("out/Events23-25_weights.db")
WEIGHT_EXPECTED_MIN = 0.7  # kg
WEIGHT_EXPECTED_MAX = 1.0  # kg

def load_events():
    """Load all events from database."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM event", conn)
    conn.close()
    return df

def calculate_tare_metrics(df):
    """Calculate tare-related metrics."""
    metrics = pd.DataFrame()

    # Tare variance (lower is better)
    metrics['tare_var_before'] = df['tare_before_var']
    metrics['tare_var_after'] = df['tare_after_var']
    metrics['tare_var_mean'] = (df['tare_before_var'] + df['tare_after_var']) / 2
    metrics['tare_var_max'] = df[['tare_before_var', 'tare_after_var']].max(axis=1)

    # Tare mean stability (before vs after, should be similar)
    metrics['tare_mean_before'] = df['tare_before_mean']
    metrics['tare_mean_after'] = df['tare_after_mean']
    metrics['tare_mean_diff'] = np.abs(df['tare_before_mean'] - df['tare_after_mean'])
    metrics['tare_mean_diff_pct'] = (metrics['tare_mean_diff'] /
                                      (np.abs(df['tare_before_mean']) + 1e-6)) * 100

    return metrics

def calculate_signal_metrics(df):
    """Calculate signal quality metrics."""
    metrics = pd.DataFrame()

    metrics['weight_median'] = df['weight_median']
    metrics['weight_var'] = df['weight_var']
    metrics['weight_std'] = np.sqrt(df['weight_var'])
    metrics['signal_cv'] = df['signal_cv_percent']
    metrics['event_range'] = df['event_range']
    metrics['event_duration_ms'] = df['event_duration_ms']
    metrics['data_points'] = df['event_data_points']

    return metrics

def print_summary_statistics(df, metrics, signal_metrics):
    """Print comprehensive summary statistics."""
    print("\n" + "="*80)
    print("EVENT QUALITY ANALYSIS - SUMMARY STATISTICS")
    print("="*80)

    print(f"\nTotal events: {len(df)}")
    print(f"Events with NaN weights: {df['weight_median'].isna().sum()}")
    print(f"Events with valid weights: {df['weight_median'].notna().sum()}")

    print("\n" + "-"*80)
    print("TARE METRICS")
    print("-"*80)

    for col in metrics.columns:
        if metrics[col].notna().sum() > 0:
            print(f"\n{col}:")
            print(f"  Mean: {metrics[col].mean():.6f}")
            print(f"  Median: {metrics[col].median():.6f}")
            print(f"  Std: {metrics[col].std():.6f}")
            print(f"  Min: {metrics[col].min():.6f}")
            print(f"  25%: {metrics[col].quantile(0.25):.6f}")
            print(f"  75%: {metrics[col].quantile(0.75):.6f}")
            print(f"  Max: {metrics[col].max():.6f}")
            print(f"  Count: {metrics[col].notna().sum()}")

    print("\n" + "-"*80)
    print("SIGNAL METRICS")
    print("-"*80)

    for col in signal_metrics.columns:
        if signal_metrics[col].notna().sum() > 0:
            print(f"\n{col}:")
            print(f"  Mean: {signal_metrics[col].mean():.6f}")
            print(f"  Median: {signal_metrics[col].median():.6f}")
            print(f"  Std: {signal_metrics[col].std():.6f}")
            print(f"  Min: {signal_metrics[col].min():.6f}")
            print(f"  25%: {signal_metrics[col].quantile(0.25):.6f}")
            print(f"  75%: {signal_metrics[col].quantile(0.75):.6f}")
            print(f"  Max: {signal_metrics[col].max():.6f}")
            print(f"  Count: {signal_metrics[col].notna().sum()}")

def classify_events_v1(df, metrics, signal_metrics):
    """
    Classification Rule V1 (Conservative):
    - Low tare variance (before AND after < 0.001)
    - Stable tare mean (diff < 1%)
    - Low weight variance (< 0.001)
    - Valid weight (not NaN)
    """
    quality = pd.DataFrame(index=df.index)
    quality['is_good'] = True

    # Check 1: Tare variances
    quality.loc[metrics['tare_var_before'] > 0.001, 'is_good'] = False
    quality.loc[metrics['tare_var_after'] > 0.001, 'is_good'] = False

    # Check 2: Tare mean stability
    quality.loc[metrics['tare_mean_diff_pct'] > 1.0, 'is_good'] = False

    # Check 3: Weight variance
    quality.loc[signal_metrics['weight_var'] > 0.001, 'is_good'] = False

    # Check 4: Valid weight
    quality.loc[signal_metrics['weight_median'].isna(), 'is_good'] = False

    return quality

def classify_events_v2(df, metrics, signal_metrics):
    """
    Classification Rule V2 (Moderate):
    - Low tare variance (before AND after < 0.0005)
    - Stable tare mean (diff < 0.5%)
    - Low weight variance (< 0.0005)
    - Valid weight
    - Weight in expected range (0.7-1.0 kg)
    """
    quality = pd.DataFrame(index=df.index)
    quality['is_good'] = True

    # Check 1: Tare variances (stricter)
    quality.loc[metrics['tare_var_before'] > 0.0005, 'is_good'] = False
    quality.loc[metrics['tare_var_after'] > 0.0005, 'is_good'] = False

    # Check 2: Tare mean stability (stricter)
    quality.loc[metrics['tare_mean_diff_pct'] > 0.5, 'is_good'] = False

    # Check 3: Weight variance (stricter)
    quality.loc[signal_metrics['weight_var'] > 0.0005, 'is_good'] = False

    # Check 4: Valid weight
    quality.loc[signal_metrics['weight_median'].isna(), 'is_good'] = False

    # Check 5: Weight in expected range
    quality.loc[signal_metrics['weight_median'] < WEIGHT_EXPECTED_MIN, 'is_good'] = False
    quality.loc[signal_metrics['weight_median'] > WEIGHT_EXPECTED_MAX, 'is_good'] = False

    return quality

def classify_events_v3(df, metrics, signal_metrics):
    """
    Classification Rule V3 (Aggressive - data-driven):
    Based on percentile analysis of actual data.
    """
    quality = pd.DataFrame(index=df.index)
    quality['is_good'] = True

    # Use percentiles instead of fixed thresholds
    tare_var_threshold = metrics['tare_var_before'].quantile(0.25)
    tare_diff_threshold = metrics['tare_mean_diff_pct'].quantile(0.25)
    weight_var_threshold = signal_metrics['weight_var'].quantile(0.25)

    quality.loc[metrics['tare_var_before'] > tare_var_threshold, 'is_good'] = False
    quality.loc[metrics['tare_var_after'] > tare_var_threshold, 'is_good'] = False
    quality.loc[metrics['tare_mean_diff_pct'] > tare_diff_threshold, 'is_good'] = False
    quality.loc[signal_metrics['weight_var'] > weight_var_threshold, 'is_good'] = False
    quality.loc[signal_metrics['weight_median'].isna(), 'is_good'] = False

    return quality

def evaluate_classification(df, quality, signal_metrics, name):
    """Evaluate and print classification results."""
    good = quality['is_good']
    bad = ~quality['is_good']

    print(f"\n{'='*80}")
    print(f"CLASSIFICATION RESULTS: {name}")
    print(f"{'='*80}")

    print(f"\nTotal events: {len(df)}")
    print(f"Good events: {good.sum()} ({100*good.sum()/len(df):.1f}%)")
    print(f"Bad events: {bad.sum()} ({100*bad.sum()/len(df):.1f}%)")

    # Weight statistics for good events
    good_weights = signal_metrics.loc[good, 'weight_median']
    print(f"\n--- GOOD EVENTS (weight distribution) ---")
    print(f"Count with weight: {good_weights.notna().sum()}")
    if good_weights.notna().sum() > 0:
        print(f"Mean weight: {good_weights.mean():.3f} kg")
        print(f"Std weight: {good_weights.std():.3f} kg")
        print(f"Min weight: {good_weights.min():.3f} kg")
        print(f"25%: {good_weights.quantile(0.25):.3f} kg")
        print(f"Median weight: {good_weights.median():.3f} kg")
        print(f"75%: {good_weights.quantile(0.75):.3f} kg")
        print(f"Max weight: {good_weights.max():.3f} kg")

        in_range = ((good_weights >= WEIGHT_EXPECTED_MIN) &
                    (good_weights <= WEIGHT_EXPECTED_MAX)).sum()
        print(f"\nWeights in expected range ({WEIGHT_EXPECTED_MIN}-{WEIGHT_EXPECTED_MAX} kg): "
              f"{in_range} ({100*in_range/good_weights.notna().sum():.1f}%)")

    # Weight statistics for bad events
    bad_weights = signal_metrics.loc[bad, 'weight_median']
    print(f"\n--- BAD EVENTS (weight distribution) ---")
    print(f"Count with weight: {bad_weights.notna().sum()}")
    if bad_weights.notna().sum() > 0:
        print(f"Mean weight: {bad_weights.mean():.3f} kg")
        print(f"Std weight: {bad_weights.std():.3f} kg")
        print(f"Min weight: {bad_weights.min():.3f} kg")
        print(f"25%: {bad_weights.quantile(0.25):.3f} kg")
        print(f"Median weight: {bad_weights.median():.3f} kg")
        print(f"75%: {bad_weights.quantile(0.75):.3f} kg")
        print(f"Max weight: {bad_weights.max():.3f} kg")

    return good, bad

def create_distributions(df, metrics, signal_metrics, quality_dict):
    """Create distribution visualizations."""
    fig, axes = plt.subplots(4, 3, figsize=(16, 14))
    fig.suptitle('Event Quality Metrics Distribution by Classification', fontsize=16, y=0.995)

    metrics_to_plot = [
        ('tare_var_before', 'Tare Var Before'),
        ('tare_var_after', 'Tare Var After'),
        ('tare_mean_diff_pct', 'Tare Mean Diff %'),
        ('weight_median', 'Weight Median (kg)'),
        ('weight_var', 'Weight Variance'),
        ('weight_std', 'Weight Std Dev'),
        ('signal_cv', 'Signal CV %'),
        ('event_duration_ms', 'Duration (ms)'),
        ('data_points', 'Data Points'),
        ('event_range', 'Event Range'),
    ]

    axes = axes.flatten()

    for idx, (col, label) in enumerate(metrics_to_plot):
        ax = axes[idx]

        for rule_name, quality in quality_dict.items():
            good = quality['is_good']

            if col in metrics.columns:
                data = metrics.loc[good, col]
            else:
                data = signal_metrics.loc[good, col]

            if data.notna().sum() > 0:
                ax.hist(data.dropna(), alpha=0.5, bins=30, label=f'{rule_name} Good')

            if col in metrics.columns:
                bad_data = metrics.loc[~good, col]
            else:
                bad_data = signal_metrics.loc[~good, col]

            if bad_data.notna().sum() > 0:
                ax.hist(bad_data.dropna(), alpha=0.5, bins=30, label=f'{rule_name} Bad')

        ax.set_xlabel(label)
        ax.set_ylabel('Count')
        ax.set_title(label)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # Remove extra subplots
    for idx in range(10, len(axes)):
        axes[idx].remove()

    plt.tight_layout()
    plt.savefig('out/event_quality_distributions.png', dpi=100, bbox_inches='tight')
    print("\nSaved: out/event_quality_distributions.png")
    plt.close()

def create_weight_distribution_plot(df, metrics, signal_metrics, quality_dict):
    """Create detailed weight distribution comparison."""
    fig, axes = plt.subplots(1, len(quality_dict), figsize=(16, 4))

    for idx, (rule_name, quality) in enumerate(quality_dict.items()):
        ax = axes[idx]

        good = quality['is_good']
        good_weights = signal_metrics.loc[good, 'weight_median'].dropna()
        bad_weights = signal_metrics.loc[~good, 'weight_median'].dropna()

        ax.hist(good_weights, bins=40, alpha=0.6, label=f'Good (n={len(good_weights)})', color='green')
        ax.hist(bad_weights, bins=40, alpha=0.6, label=f'Bad (n={len(bad_weights)})', color='red')

        ax.axvline(WEIGHT_EXPECTED_MIN, color='blue', linestyle='--', linewidth=2,
                  label=f'Expected range\n({WEIGHT_EXPECTED_MIN}-{WEIGHT_EXPECTED_MAX} kg)')
        ax.axvline(WEIGHT_EXPECTED_MAX, color='blue', linestyle='--', linewidth=2)

        ax.set_xlabel('Weight (kg)')
        ax.set_ylabel('Count')
        ax.set_title(f'{rule_name}: Weight Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('out/event_quality_weights.png', dpi=100, bbox_inches='tight')
    print("Saved: out/event_quality_weights.png")
    plt.close()

def main():
    print("Loading events...")
    df = load_events()

    print("Calculating metrics...")
    metrics = calculate_tare_metrics(df)
    signal_metrics = calculate_signal_metrics(df)

    # Print comprehensive statistics
    print_summary_statistics(df, metrics, signal_metrics)

    # Test three classification rules
    print("\n" + "="*80)
    print("TESTING CLASSIFICATION RULES")
    print("="*80)

    quality_v1 = classify_events_v1(df, metrics, signal_metrics)
    good_v1, bad_v1 = evaluate_classification(df, quality_v1, signal_metrics, "V1 (Conservative)")

    quality_v2 = classify_events_v2(df, metrics, signal_metrics)
    good_v2, bad_v2 = evaluate_classification(df, quality_v2, signal_metrics, "V2 (Moderate)")

    quality_v3 = classify_events_v3(df, metrics, signal_metrics)
    good_v3, bad_v3 = evaluate_classification(df, quality_v3, signal_metrics, "V3 (Percentile-based)")

    # Create visualizations
    print("\nGenerating visualizations...")
    quality_dict = {
        'V1': quality_v1,
        'V2': quality_v2,
        'V3': quality_v3,
    }

    create_distributions(df, metrics, signal_metrics, quality_dict)
    create_weight_distribution_plot(df, metrics, signal_metrics, quality_dict)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nVisualizations saved:")
    print("  - out/event_quality_distributions.png")
    print("  - out/event_quality_weights.png")

if __name__ == '__main__':
    main()
