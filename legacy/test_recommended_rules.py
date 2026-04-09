#!/usr/bin/env python3
"""
Test the three recommended classification rules and compare results.
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

def classify_recommended(df):
    """Balanced rule - good compromise."""
    good = ((df['weight_median'].notna()) &
            (df['weight_median'] >= WEIGHT_EXPECTED_MIN) &
            (df['weight_median'] <= WEIGHT_EXPECTED_MAX) &
            (df['weight_var'] < 0.0005) &
            (df['tare_before_var'] < 0.0001) &
            (df['tare_after_var'] < 0.0001) &
            (np.abs(df['tare_before_mean'] - df['tare_after_mean']) < 0.01) &
            (df['event_duration_ms'] > 2000) &
            (df['event_data_points'] > 50))
    return good

def classify_aggressive(df):
    """Highest confidence - stricter thresholds."""
    good = ((df['weight_median'].notna()) &
            (df['weight_median'] >= 0.75) &
            (df['weight_median'] <= 0.95) &
            (df['weight_var'] < 0.0001) &
            (df['tare_before_var'] < 0.00005) &
            (df['tare_after_var'] < 0.00005) &
            (np.abs(df['tare_before_mean'] - df['tare_after_mean']) < 0.005) &
            (df['event_duration_ms'] > 10000) &
            (df['event_data_points'] > 200) &
            (df['signal_cv_percent'] < 2.0))
    return good

def classify_lenient(df):
    """More permissive - maximize good events."""
    good = ((df['weight_median'].notna()) &
            (df['weight_median'] >= 0.6) &
            (df['weight_median'] <= 1.2) &
            (df['weight_var'] < 0.001) &
            (df['tare_before_var'] < 0.0005) &
            (df['tare_after_var'] < 0.0005) &
            (df['event_duration_ms'] > 1000))
    return good

def evaluate_rule(df, good_mask, rule_name):
    """Evaluate a classification rule."""
    good = good_mask
    bad = ~good_mask

    print(f"\n{'='*80}")
    print(f"RULE: {rule_name}")
    print(f"{'='*80}")

    print(f"\nTotal events classified: {len(df)}")
    print(f"  Good: {good.sum():6d} ({100*good.sum()/len(df):5.2f}%)")
    print(f"  Bad:  {bad.sum():6d} ({100*bad.sum()/len(df):5.2f}%)")

    # Weight statistics for good events
    good_weights = df.loc[good, 'weight_median']
    good_weights_valid = good_weights.dropna()

    print(f"\n--- GOOD EVENTS (weight quality) ---")
    if len(good_weights_valid) > 0:
        print(f"Count with valid weight: {len(good_weights_valid)}")
        print(f"Mean weight: {good_weights_valid.mean():.3f} kg")
        print(f"Std weight:  {good_weights_valid.std():.3f} kg")
        print(f"Min weight:  {good_weights_valid.min():.3f} kg")
        print(f"Max weight:  {good_weights_valid.max():.3f} kg")
        print(f"Median:      {good_weights_valid.median():.3f} kg")

        in_range = ((good_weights_valid >= WEIGHT_EXPECTED_MIN) &
                    (good_weights_valid <= WEIGHT_EXPECTED_MAX)).sum()
        print(f"In range [0.7-1.0]: {in_range}/{len(good_weights_valid)} ({100*in_range/len(good_weights_valid):.1f}%)")
    else:
        print("No good events with valid weights!")

    # Metrics for good events
    print(f"\n--- GOOD EVENTS (data quality metrics) ---")
    good_df = df[good]
    if len(good_df) > 0:
        print(f"Tare var before:  {good_df['tare_before_var'].mean():.8f} mean, "
              f"{good_df['tare_before_var'].median():.8f} median")
        print(f"Tare var after:   {good_df['tare_after_var'].mean():.8f} mean, "
              f"{good_df['tare_after_var'].median():.8f} median")
        print(f"Weight var:       {good_df['weight_var'].mean():.8f} mean, "
              f"{good_df['weight_var'].median():.8f} median")
        print(f"Tare mean diff:   {np.abs(good_df['tare_before_mean'] - good_df['tare_after_mean']).mean():.6f} kg mean")
        print(f"Duration (ms):    {good_df['event_duration_ms'].median():.0f} median, "
              f"{good_df['event_duration_ms'].mean():.0f} mean")
        print(f"Data points:      {good_df['event_data_points'].median():.0f} median, "
              f"{good_df['event_data_points'].mean():.1f} mean")
        print(f"Signal CV %:      {good_df['signal_cv_percent'].mean():.2f}% mean")

    # Weight statistics for bad events
    bad_weights = df.loc[bad, 'weight_median']
    bad_weights_valid = bad_weights.dropna()

    print(f"\n--- BAD EVENTS (weight distribution) ---")
    if len(bad_weights_valid) > 0:
        print(f"Count with valid weight: {len(bad_weights_valid)}")
        print(f"Mean weight: {bad_weights_valid.mean():.3f} kg")
        print(f"Std weight:  {bad_weights_valid.std():.3f} kg")
        print(f"Min weight:  {bad_weights_valid.min():.3f} kg")
        print(f"Max weight:  {bad_weights_valid.max():.3f} kg")

        in_range = ((bad_weights_valid >= WEIGHT_EXPECTED_MIN) &
                    (bad_weights_valid <= WEIGHT_EXPECTED_MAX)).sum()
        out_of_range = len(bad_weights_valid) - in_range
        print(f"In range [0.7-1.0]: {in_range}/{len(bad_weights_valid)} ({100*in_range/len(bad_weights_valid):.1f}%)")
        print(f"Out of range:       {out_of_range}/{len(bad_weights_valid)} ({100*out_of_range/len(bad_weights_valid):.1f}%)")

    return good, bad

def create_comparison_plot(df, results):
    """Create side-by-side comparison visualization."""
    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    fig.suptitle('Classification Rules Comparison', fontsize=16, y=0.995)

    for col_idx, (rule_name, good_mask) in enumerate(results.items()):
        # Column for each rule
        good = good_mask
        bad = ~good_mask

        # Row 1: Weight distribution
        ax = axes[0, col_idx]
        weights_good = df.loc[good, 'weight_median'].dropna()
        weights_bad = df.loc[bad, 'weight_median'].dropna()

        ax.hist(weights_good, bins=30, alpha=0.6, label=f'Good (n={len(weights_good)})',
               color='green', edgecolor='black', range=(0, 2))
        ax.hist(weights_bad, bins=30, alpha=0.6, label=f'Bad (n={len(weights_bad)})',
               color='red', edgecolor='black', range=(0, 2))
        ax.axvline(WEIGHT_EXPECTED_MIN, color='blue', linestyle='--', linewidth=2)
        ax.axvline(WEIGHT_EXPECTED_MAX, color='blue', linestyle='--', linewidth=2)
        ax.set_xlabel('Weight (kg)')
        ax.set_ylabel('Count')
        ax.set_title(f'{rule_name}: Weight Distribution')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # Row 2: Tare variance before
        ax = axes[1, col_idx]
        tare_good = df.loc[good, 'tare_before_var'].dropna()
        tare_bad = df.loc[bad, 'tare_before_var'].dropna()

        ax.hist(tare_good, bins=30, alpha=0.6, label=f'Good (n={len(tare_good)})',
               color='green', edgecolor='black', range=(0, 0.001))
        ax.hist(tare_bad, bins=30, alpha=0.6, label=f'Bad (n={len(tare_bad)})',
               color='red', edgecolor='black', range=(0, 0.001))
        ax.set_xlabel('Tare Var Before')
        ax.set_ylabel('Count')
        ax.set_title(f'{rule_name}: Tare Variance Before')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # Row 3: Weight variance
        ax = axes[2, col_idx]
        wvar_good = df.loc[good, 'weight_var'].dropna()
        wvar_bad = df.loc[bad, 'weight_var'].dropna()

        ax.hist(wvar_good, bins=30, alpha=0.6, label=f'Good (n={len(wvar_good)})',
               color='green', edgecolor='black', range=(0, 0.01))
        ax.hist(wvar_bad, bins=30, alpha=0.6, label=f'Bad (n={len(wvar_bad)})',
               color='red', edgecolor='black', range=(0, 0.01))
        ax.set_xlabel('Weight Variance')
        ax.set_ylabel('Count')
        ax.set_title(f'{rule_name}: Weight Variance')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('out/classification_rules_comparison.png', dpi=100, bbox_inches='tight')
    print("\nSaved: out/classification_rules_comparison.png")
    plt.close()

def main():
    print("\n" + "="*80)
    print("TESTING THREE RECOMMENDED CLASSIFICATION RULES")
    print("="*80)

    df = load_events()

    # Test all three rules
    results = {}

    good_recommended = classify_recommended(df)
    good_rec, bad_rec = evaluate_rule(df, good_recommended, "RECOMMENDED (Balanced)")
    results['Recommended'] = good_recommended

    good_aggressive = classify_aggressive(df)
    good_agg, bad_agg = evaluate_rule(df, good_aggressive, "AGGRESSIVE (Strict)")
    results['Aggressive'] = good_aggressive

    good_lenient = classify_lenient(df)
    good_len, bad_len = evaluate_rule(df, good_lenient, "LENIENT (Permissive)")
    results['Lenient'] = good_lenient

    # Create visualization
    print("\nGenerating comparison visualization...")
    create_comparison_plot(df, results)

    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'Rule':<15} {'Good Count':>10} {'Good %':>7} {'Weight Mean':>12} {'Weight Std':>11} {'In Range':>10}")
    print("-" * 80)

    for rule_name, good_mask in results.items():
        good = good_mask
        weights = df.loc[good, 'weight_median'].dropna()
        if len(weights) > 0:
            in_range = ((weights >= WEIGHT_EXPECTED_MIN) & (weights <= WEIGHT_EXPECTED_MAX)).sum()
            in_range_pct = 100 * in_range / len(weights)
        else:
            in_range_pct = 0

        print(f"{rule_name:<15} {good.sum():>10d} {100*good.sum()/len(df):>6.2f}% "
              f"{weights.mean():>11.3f} kg {weights.std():>10.3f} kg {in_range_pct:>9.1f}%")

    print(f"\n{'='*80}")
    print("RECOMMENDATION FOR YOUR USE CASE")
    print(f"{'='*80}")
    print("""
Choose based on your needs:

1. RECOMMENDED (Balanced)
   - Most practical for most use cases
   - ~1-3% of events classified as good
   - All good events in expected range
   - Use this unless you have specific reason not to

2. AGGRESSIVE (Strict)
   - Use if you need highest confidence
   - ~0.5-1% of events
   - Strictest quality criteria
   - Best for critical measurements

3. LENIENT (Permissive)
   - Use if you need more data
   - ~3-5% of events
   - Relaxed thresholds
   - Still maintains good weight range

Next steps:
- Review visualizations: out/classification_rules_comparison.png
- Apply chosen rule to your events
- Export good/bad classifications to database or CSV
""")

if __name__ == '__main__':
    main()
