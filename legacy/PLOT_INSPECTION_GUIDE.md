# Quality Classification Plot Inspection Guide

## Generated Plots Summary
- **Q2 (RECOMMENDED)**: 100 plots - 10 per station, 11,441 total events (25% of dataset)
- **Q3 (AGGRESSIVE)**: 90 plots - 10 per 9 stations, 3,257 total events (7.1% of dataset)
- **Location**: `out/quality_classifications_v2/`

## What Each Plot Shows

Each plot displays one event with:
- **Blue line**: Raw signal from the weight sensor
- **Green span**: Tare baseline BEFORE event (bird approaching)
- **Red span**: Event window (bird on scale, +1s start delay, -1s end delay)
- **Orange span**: Tare baseline AFTER event (bird leaving)
- **Vertical dashed lines**: Event start and end boundaries

## How to Use These for Decision-Making

### Q2 vs Q3 Comparison Categories

Watch for these patterns as you review:

1. **Signal Stability**
   - **Q2 events**: May show more baseline jitter 0.5-2% CV
   - **Q3 events**: Should show ultra-stable baseline <2% CV
   - Look at the green and orange spans - do they look "flat" or "noisy"?

2. **Event Duration**
   - **Q2 events**: Many 2-5 seconds (minimal data)
   - **Q3 events**: All ≥10 seconds (plenty of data)
   - Longer duration = more data points = more reliable average

3. **Weight Range**
   - **Q2 events**: 0.7-1.0 kg (includes edge cases)
   - **Q3 events**: 0.75-0.95 kg (sweet spot for typical birds)
   - Look at the red span height - is it visually consistent?

4. **Tare Quality**
   - **Q2 events**: More drift between before/after tare (|Δ| < 0.01 kg allowed)
   - **Q3 events**: Very stable tare (|Δ| < 0.005 kg)
   - Compare green and orange spans - do they align horizontally?

## Key Decisions to Make

### 1. Data Quality vs. Volume Trade-off
- **Q2 captures 11,441 events** but some may be noisy/marginal
- **Q3 captures 3,257 events** but all are high-quality

### 2. Usability per Station
Look at patterns across 10 samples from each station:
- Do **Q2** and **Q3** events look dramatically different?
- Are **Q3** events clearly "cleaner" or marginally better?
- Some stations may have more **Q3** candidates than others

### 3. Visual Inspection Observations

As you flip through the plots, note:

| Observation | Meaning |
|---|---|
| Clean, centered weight plateau in red span | Good event |
| Wobbly/noisy weight signal | Poor sensor stability |
| Asymmetric ramp-up vs ramp-down | Possible detection boundary issues |
| Green/orange spans not at baseline | Possible scale drift or environmental vibration |
| Tiny red span with few data points | Short event (↑ measurement error) |
| Large weight fluctuations (±0.1 kg) | High noise → need Q3 strictness |

## Next Steps

After reviewing plots, you can decide:
- **Go with Q2**: Maximize data volume with acceptable quality
- **Go with Q3**: Maximize data quality with reduced volume
- **Hybrid**: Use Q2 for some analyses, Q3 for others
- **Modified thresholds**: Combine aspects of both (e.g., Q2 duration + Q3 weight variance)

## File Organization

```
out/quality_classifications_v2/
├── Q2_RECOMMENDED_BJORN3TRI3_SCALE_event01.png
├── Q2_RECOMMENDED_BJORN3TRI3_SCALE_event02.png
├── ...
├── Q2_RECOMMENDED_TRI5_SCALE_event10.png
├── Q3_AGGRESSIVE_BJORN3TRI3_SCALE_event01.png
├── Q3_AGGRESSIVE_BJORN3TRI3_SCALE_event02.png
├── ...
└── Q3_AGGRESSIVE_TRI5_SCALE_event10.png
```

All files follow naming: `{QUALITY_TIER}_{STATION}_{event_number}.png`
