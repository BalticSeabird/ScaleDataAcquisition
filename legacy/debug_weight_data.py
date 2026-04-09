"""
Comprehensive Data Quality Analysis for Weight Events
Investigates low weight values, missing data, and event detection issues
"""

import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import json
from collections import defaultdict

# Set style for better plots
plt.rcParams['figure.figsize'] = (14, 8)

def load_db(db_path: Path, table="cells"):
    """Load database into dataframe"""
    con = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f'SELECT * from {table}', con).sort_values(by=["timestamp"])
    except Exception as e:
        print(f'Error loading {db_path.name}: {e}')
        df = pd.DataFrame()
    con.close()
    return df

def analyze_weight_quality(station_name="FAR3BONDEN3", exclude_stations=["ROST2", "FAR8DHOLK", "BONDEN1"]):
    """
    Main analysis function for weight data quality
    """

    print("\n" + "="*100)
    print(f"WEIGHT DATA QUALITY ANALYSIS: {station_name}")
    print("="*100 + "\n")

    # Load events database if it exists
    events_db = Path("out/Events23-25.db")
    if not events_db.exists():
        print(f"⚠️  Events database not found at {events_db}")
        print("   Please run step1_state_machine_fast.py first")
        return

    con_events = sqlite3.connect(events_db)
    events_df = pd.read_sql_query("SELECT * FROM event", con_events)
    con_events.close()

    # Load scale names
    with open("config/ScaleSystemNames.json", "r") as f:
        lookup_data = json.load(f)
    lookup = pd.DataFrame(lookup_data["scale_system_mappings"])

    # Find the DGT and cell for this station
    station_info = lookup[lookup["scalename"] == station_name]
    if station_info.empty:
        print(f"❌ Station {station_name} not found in config")
        return

    dgt = station_info.iloc[0]["dgt"]
    cell = station_info.iloc[0]["cell"]
    print(f"Found {station_name}: DGT={dgt}, Cell={cell}\n")

    # Filter events for this station
    station_events = events_df[(events_df["DGT"] == dgt) & (events_df["cell"] == cell)].copy()
    print(f"Total events for {station_name}: {len(station_events)}\n")

    if len(station_events) == 0:
        print("No events found for this station!")
        return

    # Get unique database files for this station
    unique_dbs = station_events["db_name"].unique()
    print(f"Database files to analyze: {len(unique_dbs)}\n")

    # Initialize analysis containers
    analysis_results = {
        'very_low_weights': [],
        'missing_weights': [],
        'short_events': [],
        'unstable_tare': [],
        'zero_event_weight': [],
        'negative_weight': [],
        'suspicious_events': []
    }

    # Parameters (same as in step2)
    tare_length = 10000  # ms
    start_delay = 2000   # ms

    # Thresholds for analysis
    MIN_WEIGHT = 0.3  # kg - suspiciously low
    MAX_WEIGHT = 1.5  # kg - suspiciously high
    MIN_EVENT_DURATION = 1000  # ms
    TARE_STABILITY_THRESHOLD = 0.2  # kg

    # Storage for plotting later
    all_events_data = []

    print("Analyzing events in detail...\n")

    # Analyze each database file
    for db_file in unique_dbs:
        db_path = list(Path('../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(db_file))

        if not db_path:
            print(f"⚠️  Could not find {db_file}")
            continue

        print(f"Processing {db_file}...")
        data = load_db(db_path[0])

        if data.empty or len(data) < 10:
            print(f"  ⚠️  Insufficient data")
            continue

        # Get events for this file
        file_events = station_events[station_events["db_name"] == db_file].reset_index(drop=True)

        # Analyze each event
        for idx, event in file_events.iterrows():
            start = event["Event_start"]
            end = event["Event_end"]
            event_duration = end - start

            # Extract weight data
            cond1 = data["timestamp"] > start + start_delay
            cond2 = data["timestamp"] < end - start_delay
            cond3 = data["timestamp"] > start - tare_length
            cond4 = data["timestamp"] <= start
            cond5 = data["timestamp"] >= end
            cond6 = data["timestamp"] < end + tare_length

            data_event = data[cond1 & cond2][f"cell_{cell}"]
            data_before = data[cond3 & cond4][f"cell_{cell}"]
            data_after = data[cond5 & cond6][f"cell_{cell}"]

            # Calculate metrics
            event_count = len(data_event)
            before_count = len(data_before)
            after_count = len(data_after)

            if len(data_event) > 5:
                weight_med = data_event.median()
                tare_before = data_before.median()
                tare_after = data_after.median()
                tare_avg = (tare_before + tare_after) / 2
                corrected_weight = weight_med - tare_avg
                weight_var = data_event.var()

                # Flag issues
                event_dict = {
                    'db_file': db_file,
                    'event_idx': idx,
                    'start': start,
                    'end': end,
                    'duration_ms': event_duration,
                    'event_count': event_count,
                    'before_count': before_count,
                    'after_count': after_count,
                    'raw_weight_median': weight_med,
                    'tare_before': tare_before,
                    'tare_after': tare_after,
                    'tare_avg': tare_avg,
                    'corrected_weight': corrected_weight,
                    'weight_var': weight_var,
                    'issues': []
                }

                # Detect issues
                if corrected_weight < MIN_WEIGHT:
                    event_dict['issues'].append(f"VERY_LOW_WEIGHT({corrected_weight:.3f}kg)")
                    analysis_results['very_low_weights'].append(event_dict)

                if corrected_weight < 0.01:
                    event_dict['issues'].append("NEGATIVE/ZERO_WEIGHT")
                    analysis_results['zero_event_weight'].append(event_dict)

                if corrected_weight < 0:
                    analysis_results['negative_weight'].append(event_dict)

                if event_duration < MIN_EVENT_DURATION:
                    event_dict['issues'].append(f"SHORT_EVENT({event_duration:.0f}ms)")
                    analysis_results['short_events'].append(event_dict)

                if abs(tare_before - tare_after) > TARE_STABILITY_THRESHOLD:
                    event_dict['issues'].append(f"UNSTABLE_TARE(diff={abs(tare_before - tare_after):.3f}kg)")
                    analysis_results['unstable_tare'].append(event_dict)

                if before_count < 10 or after_count < 10:
                    event_dict['issues'].append(f"INSUFFICIENT_TARE_DATA(before={before_count}, after={after_count})")

                if len(event_dict['issues']) > 0:
                    analysis_results['suspicious_events'].append(event_dict)

                all_events_data.append(event_dict)
            else:
                # Not enough data points
                analysis_results['missing_weights'].append({
                    'db_file': db_file,
                    'event_idx': idx,
                    'event_count': event_count,
                    'before_count': before_count,
                    'after_count': after_count
                })

        print(f"  ✓ {len(file_events)} events analyzed\n")

    # Print summary report
    print("\n" + "="*100)
    print("SUMMARY REPORT")
    print("="*100 + "\n")

    if all_events_data:
        df_all = pd.DataFrame(all_events_data)

        print(f"Total events analyzed: {len(df_all)}")
        print(f"Events with issues: {len(analysis_results['suspicious_events'])}\n")

        print("Issue Breakdown:")
        print(f"  - Very low weights (<{MIN_WEIGHT}kg): {len(analysis_results['very_low_weights'])}")
        print(f"  - Missing weight data: {len(analysis_results['missing_weights'])}")
        print(f"  - Short events (<{MIN_EVENT_DURATION}ms): {len(analysis_results['short_events'])}")
        print(f"  - Unstable tare (diff >{TARE_STABILITY_THRESHOLD}kg): {len(analysis_results['unstable_tare'])}")
        print(f"  - Zero/negative weight: {len(analysis_results['zero_event_weight'])}")

        print(f"\nWeight Statistics:")
        print(f"  Mean corrected weight: {df_all['corrected_weight'].mean():.3f} kg")
        print(f"  Median corrected weight: {df_all['corrected_weight'].median():.3f} kg")
        print(f"  Min corrected weight: {df_all['corrected_weight'].min():.3f} kg")
        print(f"  Max corrected weight: {df_all['corrected_weight'].max():.3f} kg")
        print(f"  Std dev: {df_all['corrected_weight'].std():.3f} kg")

        print(f"\nEvent Duration Statistics:")
        print(f"  Mean duration: {df_all['duration_ms'].mean():.0f} ms")
        print(f"  Min duration: {df_all['duration_ms'].min():.0f} ms")
        print(f"  Max duration: {df_all['duration_ms'].max():.0f} ms")

        print(f"\nTare Stability:")
        if analysis_results['suspicious_events']:
            suspic_df = pd.DataFrame(analysis_results['suspicious_events'])
            if 'tare_before' in suspic_df.columns:
                tare_diffs = abs(suspic_df['tare_before'] - suspic_df['tare_after'])
                print(f"  Problematic tare diffs - Mean: {tare_diffs.mean():.3f}, Max: {tare_diffs.max():.3f} kg")

        # Show worst cases
        print("\n" + "-"*100)
        print("TOP 10 MOST PROBLEMATIC EVENTS")
        print("-"*100 + "\n")

        sorted_events = sorted(analysis_results['suspicious_events'],
                             key=lambda x: len(x['issues']), reverse=True)

        for i, event in enumerate(sorted_events[:10], 1):
            print(f"{i}. Event from {event['db_file']} (idx {event['event_idx']})")
            print(f"   Duration: {event['duration_ms']:.0f}ms | Corrected weight: {event['corrected_weight']:.4f} kg")
            print(f"   Raw weight: {event['raw_weight_median']:.4f} | Tare: {event['tare_avg']:.4f} | Var: {event['weight_var']:.4f}")
            print(f"   Data points - Event: {event['event_count']}, Before: {event['before_count']}, After: {event['after_count']}")
            print(f"   Issues: {', '.join(event['issues'])}\n")

        # Create visualizations
        create_visualizations(station_name, all_events_data, analysis_results, dgt, cell)

        # Generate recommendations
        print("\n" + "="*100)
        print("RECOMMENDATIONS")
        print("="*100 + "\n")
        generate_recommendations(analysis_results, station_name, df_all)

    return analysis_results, all_events_data

def create_visualizations(station_name, all_events_data, analysis_results, dgt, cell):
    """Create comprehensive visualization plots"""

    df_all = pd.DataFrame(all_events_data)

    # Create output directory
    Path("out/figs").mkdir(parents=True, exist_ok=True)

    # 1. Weight distribution histogram
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Weight Data Quality Analysis - {station_name}', fontsize=16, fontweight='bold')

    ax = axes[0, 0]
    ax.hist(df_all['corrected_weight'], bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(df_all['corrected_weight'].mean(), color='red', linestyle='--', linewidth=2, label='Mean')
    ax.axvline(df_all['corrected_weight'].median(), color='green', linestyle='--', linewidth=2, label='Median')
    ax.axvspan(0.7, 1.0, alpha=0.2, color='blue', label='Expected range')
    ax.set_xlabel('Corrected Weight (kg)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Corrected Weights')
    ax.legend()

    # 2. Event duration distribution
    ax = axes[0, 1]
    ax.hist(df_all['duration_ms'], bins=50, edgecolor='black', alpha=0.7, color='orange')
    ax.axvline(df_all['duration_ms'].mean(), color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('Event Duration (ms)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Event Durations')
    ax.grid(True, alpha=0.3)

    # 3. Weight vs Duration scatter
    ax = axes[1, 0]
    scatter = ax.scatter(df_all['duration_ms'], df_all['corrected_weight'],
                        c=df_all['weight_var'], cmap='viridis', alpha=0.6, s=50)
    ax.set_xlabel('Event Duration (ms)')
    ax.set_ylabel('Corrected Weight (kg)')
    ax.set_title('Weight vs Duration (colored by variance)')
    ax.axhspan(0.7, 1.0, alpha=0.1, color='blue')
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Weight Variance')
    ax.grid(True, alpha=0.3)

    # 4. Tare stability
    ax = axes[1, 1]
    tare_diffs = abs(df_all['tare_before'] - df_all['tare_after'])
    ax.hist(tare_diffs, bins=50, edgecolor='black', alpha=0.7, color='red')
    ax.axvline(tare_diffs.mean(), color='darkred', linestyle='--', linewidth=2, label='Mean')
    ax.axvline(0.2, color='orange', linestyle='--', linewidth=2, label='Threshold')
    ax.set_xlabel('Tare Difference (kg)')
    ax.set_ylabel('Frequency')
    ax.set_title('Tare Baseline Stability (|before - after|)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'out/figs/{station_name}_quality_overview.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved overview plot: out/figs/{station_name}_quality_overview.png")

    # 5. Detailed low-weight events visualization
    if analysis_results['very_low_weights']:
        fig, axes = plt.subplots(3, 2, figsize=(14, 12))
        fig.suptitle(f'Very Low Weight Events (< 0.3kg) - {station_name}', fontsize=14, fontweight='bold')

        low_weight_events = sorted(analysis_results['very_low_weights'],
                                  key=lambda x: x['corrected_weight'])[:6]

        for idx, (ax, event) in enumerate(zip(axes.flat, low_weight_events)):
            db_file = event['db_file']
            db_path = list(Path('../../../../../../mnt/BSP_NAS2/Other_sensors/weightlog/').rglob(db_file))

            if db_path:
                data = load_db(db_path[0])

                start = event['start'] - 5000  # Show 5 seconds before
                end = event['end'] + 5000      # Show 5 seconds after

                window_data = data[(data['timestamp'] >= start) & (data['timestamp'] <= end)]

                if not window_data.empty:
                    timestamps = (window_data['timestamp'] - start) / 1000  # Convert to seconds
                    ax.plot(timestamps, window_data[f'cell_{cell}'], linewidth=1, alpha=0.8)

                    # Mark event boundaries
                    ax.axvline((event['start'] - start) / 1000, color='green', linestyle='--', alpha=0.7, label='Event start')
                    ax.axvline((event['end'] - start) / 1000, color='red', linestyle='--', alpha=0.7, label='Event end')

                    ax.set_title(f"Weight: {event['corrected_weight']:.4f}kg, Duration: {event['duration_ms']:.0f}ms")
                    ax.set_xlabel('Time (s)')
                    ax.set_ylabel('Weight (kg)')
                    ax.grid(True, alpha=0.3)
                    ax.legend(fontsize=8)

        plt.tight_layout()
        plt.savefig(f'out/figs/{station_name}_low_weight_events.png', dpi=150, bbox_inches='tight')
        print(f"✓ Saved low-weight events plot: out/figs/{station_name}_low_weight_events.png")

    plt.close('all')

def generate_recommendations(analysis_results, station_name, df_all):
    """Generate specific recommendations based on findings"""

    total_events = len(df_all)
    pct_problematic = len(analysis_results['suspicious_events']) / total_events * 100 if total_events > 0 else 0

    print(f"Station: {station_name}")
    print(f"Problem Events: {pct_problematic:.1f}% of all events\n")

    # Analysis 1: Very low weights
    if analysis_results['very_low_weights']:
        pct = len(analysis_results['very_low_weights']) / total_events * 100
        print(f"1. VERY LOW WEIGHTS ({pct:.1f}% of events)")
        print("   Possible causes:")
        print("   - Threshold in event detector (0.6kg) is too low for small birds")
        print("   - Sensor noise being detected as events")
        print("   - Tare subtraction is overcorrecting (tare value too high)")
        print("   Recommendations:")
        print("   ✓ Increase detection threshold from 0.6kg to 0.8-1.0kg")
        print("   ✓ Review tare calculation - ensure tare baseline is stable")
        print("   ✓ Add minimum weight filter: reject events < 0.4kg as noise\n")

    # Analysis 2: Short events
    if analysis_results['short_events']:
        pct = len(analysis_results['short_events']) / total_events * 100
        mean_short_dur = np.mean([e['duration_ms'] for e in analysis_results['short_events']])
        print(f"2. SHORT EVENTS ({pct:.1f}% of events, mean duration: {mean_short_dur:.0f}ms)")
        print("   Possible causes:")
        print("   - Brief vibrations or sensor fluctuations detected as events")
        print("   - Window size (30) in sliding median not filtering noise properly")
        print("   Recommendations:")
        print("   ✓ Implement minimum event duration: 2000ms (2 seconds)")
        print("   ✓ Increase sliding window from 30 to 50-80 samples\n")

    # Analysis 3: Unstable tare
    if analysis_results['unstable_tare']:
        pct = len(analysis_results['unstable_tare']) / total_events * 100
        print(f"3. UNSTABLE TARE BASELINE ({pct:.1f}% of events)")
        print("   Possible causes:")
        print("   - Scale not stable before/after event")
        print("   - 10-second tare window too small to capture stability")
        print("   - Environmental factors affecting baseline")
        print("   Recommendations:")
        print("   ✓ Increase tare window from 10 to 20 seconds")
        print("   ✓ Require tare stability: reject if before/after differ > 0.1kg")
        print("   ✓ Use longer median window for tare (not just 1 value before/after)\n")

    # Analysis 4: Missing data
    if analysis_results['missing_weights']:
        pct = len(analysis_results['missing_weights']) / total_events * 100
        print(f"4. MISSING WEIGHT DATA ({pct:.1f}% of events)")
        print("   Possible causes:")
        print("   - Start/end delay windows remove all event data")
        print("   - Very short events combined with 2-second delay = no data")
        print("   Recommendations:")
        print("   ✓ Reduce start_delay from 2000ms to 1000ms")
        print("   ✓ Or implement minimum event duration filter first\n")

    # Analysis 5: General recommendations
    print("5. GENERAL RECOMMENDATIONS FOR IMPROVEMENT")
    print("   Priority (HIGH):")
    print("   • Increase event detection threshold to 0.8-1.0kg")
    print("   • Implement minimum duration filter (2000ms)")
    print("   • Add post-detection weight validation (0.4-1.5kg range)")
    print("   ")
    print("   Priority (MEDIUM):")
    print("   • Increase sliding window for detection (30 → 50)")
    print("   • Increase tare window (10s → 20s)")
    print("   • Review and stabilize sensor baseline")
    print("   ")
    print("   Priority (LOW):")
    print("   • Fine-tune variance thresholds")
    print("   • Consider adaptive thresholds based on time of day")
    print("   • Add signal smoothing/filtering\n")

    # Specific note for this station
    print(f"6. STATION-SPECIFIC NOTES FOR {station_name}")
    if analysis_results['very_low_weights']:
        print(f"   ⚠️  {len(analysis_results['very_low_weights'])} events with suspiciously low weights")
        print(f"      This suggests the event detector is catching small variations")
        print(f"      that are not actual bird landings.")
    if analysis_results['short_events']:
        print(f"   ⚠️  {len(analysis_results['short_events'])} very short events")
        print(f"      Recommend filtering to events > 2000ms")
    if analysis_results['unstable_tare']:
        print(f"   ⚠️  {len(analysis_results['unstable_tare'])} events with unstable tare")
        print(f"      This could cause weight miscalculation")

if __name__ == "__main__":
    # Run analysis for FAR3BONDEN3
    analysis_results, all_events = analyze_weight_quality(
        station_name="FAR3BONDEN3",
        exclude_stations=["ROST2", "FAR8DHOLK", "BONDEN1"]
    )

    print("\n" + "="*100)
    print("Analysis complete! Check out/figs/ for detailed visualizations.")
    print("="*100 + "\n")
