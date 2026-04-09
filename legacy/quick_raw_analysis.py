"""
Quick analysis of weight data quality - works directly with raw weight data
No need to wait for full pipeline processing
"""

import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

plt.rcParams['figure.figsize'] = (14, 8)

def load_db(db_path: Path):
    """Load database into dataframe"""
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * from cells", con).sort_values(by=["timestamp"])
    except Exception as e:
        print(f'Error: {e}')
        df = pd.DataFrame()
    con.close()
    return df

def analyze_station_raw_data(station_name="FAR3BONDEN3", dgt="dgt2", cell=1):
    """
    Analyze raw weight data directly without running event detector
    Shows baseline noise, signal patterns, stability issues
    """
    print("\n" + "="*100)
    print(f"RAW WEIGHT DATA ANALYSIS: {station_name} (DGT={dgt}, Cell={cell})")
    print("="*100 + "\n")

    # Find all database files
    nas_path = Path('../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/')
    db_files = sorted(list(nas_path.rglob("*.db")))[-50:]  # Last 50 files for recent data

    if not db_files:
        print("❌ No database files found!")
        return

    print(f"Found {len(db_files)} database files\n")

    all_sessions = []
    cell_column = f"cell_{cell}"

    # Analyze each database file
    for db_file in db_files[-10:]:  # Last 10 files for recent data
        print(f"Processing {db_file.name}...", end=" ")

        data = load_db(db_file)

        if data.empty or cell_column not in data.columns:
            print("❌ No data")
            continue

        weights = data[cell_column]

        # Calculate statistics
        stats = {
            'file': db_file.name,
            'rows': len(data),
            'mean': weights.mean(),
            'median': weights.median(),
            'std': weights.std(),
            'min': weights.min(),
            'max': weights.max(),
            'range': weights.max() - weights.min(),
            'q25': weights.quantile(0.25),
            'q75': weights.quantile(0.75),
            'iqr': weights.quantile(0.75) - weights.quantile(0.25),
            'nonzero_count': (weights > 0.01).sum(),
            'values_below_01': (weights < 0.1).sum(),
            'values_below_03': (weights < 0.3).sum(),
        }

        all_sessions.append(stats)
        print(f"✓ (mean={stats['mean']:.3f}, std={stats['std']:.3f})")

    print()

    if not all_sessions:
        print("❌ No valid data found!")
        return

    # Summary statistics
    df_stats = pd.DataFrame(all_sessions)

    print("="*100)
    print("RAW DATA QUALITY FINDINGS")
    print("="*100 + "\n")

    print("Baseline Statistics (across all files):")
    print(f"  Mean baseline weight: {df_stats['mean'].mean():.4f} kg")
    print(f"  Median baseline weight: {df_stats['median'].mean():.4f} kg")
    print(f"  Std dev (consistency): {df_stats['std'].mean():.4f} kg")
    print(f"  Average range: {df_stats['range'].mean():.4f} kg")
    print(f"  Average IQR: {df_stats['iqr'].mean():.4f} kg\n")

    print("Data Quality Issues:")
    total_files = len(df_stats)
    files_below_01 = (df_stats['values_below_01'] > 0).sum()
    files_below_03 = (df_stats['values_below_03'] > 0).sum()

    print(f"  Files with values < 0.1kg: {files_below_01}/{total_files} ({files_below_01/total_files*100:.1f}%)")
    print(f"  Files with values < 0.3kg: {files_below_03}/{total_files} ({files_below_03/total_files*100:.1f}%)")
    print()

    # Analysis of noise
    print("Noise Analysis:")
    high_std_files = df_stats[df_stats['std'] > df_stats['std'].quantile(0.75)]
    if len(high_std_files) > 0:
        print(f"  High variability files: {len(high_std_files)}")
        print(f"    Std dev range: {high_std_files['std'].min():.4f} - {high_std_files['std'].max():.4f} kg")
    print()

    # Stability check
    print("Baseline Stability:")
    mean_variation = df_stats['mean'].std()
    print(f"  Variation in mean across files: {mean_variation:.4f} kg")
    if mean_variation > 0.1:
        print(f"  ⚠️  UNSTABLE BASELINE - may affect weight calculations")
    print()

    # Visualize
    create_raw_data_plots(all_sessions, station_name, dgt, cell)

    # Get threshold insights
    get_threshold_insights(df_stats, station_name)

    return df_stats

def create_raw_data_plots(all_sessions, station_name, dgt, cell):
    """Create visualization of raw data characteristics"""

    Path("out/figs").mkdir(parents=True, exist_ok=True)

    df_stats = pd.DataFrame(all_sessions)

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle(f'Raw Weight Data Analysis - {station_name}', fontsize=14, fontweight='bold')

    # 1. Mean baseline across files
    ax = axes[0, 0]
    ax.plot(df_stats['mean'], marker='o', alpha=0.7, linewidth=2)
    ax.axhline(df_stats['mean'].mean(), color='r', linestyle='--', label='Average')
    ax.fill_between(range(len(df_stats)), df_stats['mean'] - df_stats['std'],
                     df_stats['mean'] + df_stats['std'], alpha=0.2)
    ax.set_xlabel('File #')
    ax.set_ylabel('Weight (kg)')
    ax.set_title('Baseline Mean (with ±1 Std Dev)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Variability
    ax = axes[0, 1]
    ax.bar(range(len(df_stats)), df_stats['std'], alpha=0.7, color='orange')
    ax.axhline(df_stats['std'].mean(), color='r', linestyle='--', label='Average')
    ax.set_xlabel('File #')
    ax.set_ylabel('Std Dev (kg)')
    ax.set_title('Signal Variability')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Range
    ax = axes[0, 2]
    ax.bar(range(len(df_stats)), df_stats['range'], alpha=0.7, color='green')
    ax.axhline(df_stats['range'].mean(), color='r', linestyle='--', label='Average')
    ax.set_xlabel('File #')
    ax.set_ylabel('Range (kg)')
    ax.set_title('Min-Max Range')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 4. Distribution of mean values
    ax = axes[1, 0]
    ax.hist(df_stats['mean'], bins=15, edgecolor='black', alpha=0.7)
    ax.axvline(df_stats['mean'].mean(), color='r', linestyle='--', linewidth=2, label='Mean')
    ax.set_xlabel('Baseline Mean (kg)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Baseline Means')
    ax.legend()

    # 5. Count of problematic values
    ax = axes[1, 1]
    problematic_counts = [
        df_stats['values_below_01'].sum(),
        df_stats['values_below_03'].sum(),
        (df_stats['values_below_03'] - df_stats['values_below_01']).sum()
    ]
    labels = ['< 0.1kg', '< 0.3kg', '0.1-0.3kg']
    colors = ['red', 'orange', 'yellow']
    bars = ax.bar(labels, problematic_counts, color=colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Count of measurements')
    ax.set_title('Problematic Low-Weight Measurements')
    ax.grid(True, alpha=0.3, axis='y')
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom')

    # 6. Stability metric
    ax = axes[1, 2]
    ax.scatter(df_stats['mean'], df_stats['std'], s=100, alpha=0.6, edgecolors='black')
    ax.set_xlabel('Mean Baseline (kg)')
    ax.set_ylabel('Std Dev (kg)')
    ax.set_title('Baseline vs Variability')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'out/figs/{station_name}_raw_data_analysis.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved plot: out/figs/{station_name}_raw_data_analysis.png")
    plt.close()

def get_threshold_insights(df_stats, station_name):
    """Analyze what threshold would be appropriate"""

    print("\n" + "="*100)
    print("THRESHOLD RECOMMENDATIONS")
    print("="*100 + "\n")

    mean_baseline = df_stats['mean'].mean()
    std_baseline = df_stats['std'].mean()

    print(f"Current Baseline Characteristics:")
    print(f"  Mean: {mean_baseline:.4f} kg")
    print(f"  Std Dev: {std_baseline:.4f} kg")
    print(f"  3-sigma: {mean_baseline + 3*std_baseline:.4f} kg\n")

    print(f"Proposed Detection Thresholds:")
    print(f"  Very safe (mean + 2σ): {mean_baseline + 2*std_baseline:.4f} kg")
    print(f"  Safe (mean + 3σ): {mean_baseline + 3*std_baseline:.4f} kg")
    print(f"  Moderate (0.6 kg): Current setting")
    print(f"  Conservative (0.8 kg): Recommended minimum\n")

    # Sanity check
    if mean_baseline < 0.1:
        print(f"⚠️  WARNING: Baseline is extremely low ({mean_baseline:.4f} kg)")
        print("   This suggests:")
        print("   - Sensor may need recalibration")
        print("   - Sensor may not be zeroed properly")
        print("   - There may be data quality issues\n")

    if std_baseline > 0.2:
        print(f"⚠️  WARNING: High baseline noise ({std_baseline:.4f} kg)")
        print("   This suggests:")
        print("   - Scale is not stable")
        print("   - Environmental vibrations may be present")
        print("   - Sensor needs recalibration")
        print("   Recommendation: Increase detection threshold or smooth signal\n")

if __name__ == "__main__":
    # Analyze FAR3BONDEN3
    stats = analyze_station_raw_data(
        station_name="FAR3BONDEN3",
        dgt="dgt2",
        cell=1
    )

    print("\n" + "="*100)
    print("Quick analysis complete!")
    print("="*100)
