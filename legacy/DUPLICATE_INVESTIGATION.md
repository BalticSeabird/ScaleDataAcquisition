# Duplicate Events Investigation for 2024 Data

## Finding Summary
**Every unique event in 2024 data appears EXACTLY TWICE** in the Events23-25.db database, while 2023 data has NO duplicates.

### Evidence
- **2024**: 41,406 total rows = 20,703 unique events × 2
- **2023**: 10,848 total rows (all unique, no duplicates)
- **2025**: Different issue (same Event_start but different Event_end values)
- **Example**: File `20240711_dgt2.db`, cell 4:
  - Event `1720662200252.0 → 1720662206472.0` appears TWICE consecutively
  - ALL 139 unique events in this cell are doubled

## Likely Root Causes

### 1. **MOST LIKELY: Pandas DataFrame Concatenation Logic** ⚠️

**Location**: Lines 87-91 in `step1_state_machine_fast.py`

```python
d = {"Event_start": list(event_start_idx),
    "Event_end": list(event_end_idx),
    "Event_start_time": list(event_start),
    "Event_end_time": list(event_end)}
event_list = pd.DataFrame(d)
```

**The Problem**:
- If `event_start_idx` (list length N) and `event_end_idx` (list length N) are created from different pandas Series indexing operations, they might have duplicated indices
- When the state changes are detected, pandas might return duplicated indices if the state vector has repeated values
- The subsequent DataFrame creation would preserve these duplicates

**Why only 2024?**
- Possible code changes between 2023 and 2024 processing
- Different data characteristics in 2024 (more noise?), causing different state transitions
- The bug might have existed but manifested differently depending on the data pattern

### 2. **Multiple Runs Against Same Database **

**Location**: Line 39 - Database initialization

```python
if os.path.exists("out/Events23-25.db"):
    os.remove("out/Events23-25.db")
con_local = create_connection("out/Events23-25.db")
```

**The Problem**:
- If this script was run twice on the same source database file, it would append new records
- However, this should only happen if the script was explicitly re-run
- **But**: If the script ran partially then resumed, or if there's a recovery/retry mechanism, duplicates could accumulate

**Evidence Against**:
- 2023 data doesn't have duplicates, so this would have affected all years equally

### 3. **State Change Detection Producing Duplicates**

**Location**: Lines 79-85

```python
state = np.where(median_vect > threshold, 1, 0)
state = np.concat((state[halfwindow:], np.repeat(0, halfwindow)), axis=0)
statechange = pd.Series(state).diff().fillna(0).astype("int")
event_start = ts[statechange == 1]
event_end = ts[statechange == -1]
```

**The Problem**:
- The padding logic (line 80) is non-standard. It removes `halfwindow` entries from start and adds zeros to end
- This artificial padding could create false state transitions
- If the last `halfwindow` entries had state=1 (on scale), padding with 0s creates an artificial "off" transition
- Similarly, the first entries being removed could create mismatched on/off pairs

**Why only 2024?**
- Maybe 2024 data has more frequent scale usage ending right at the end of collection window
- Or 2024 has longer events that happen to hit these edge cases

### 4. **Index Alignment Issue in DataFrame Creation**

**Location**: Lines 87-94

```python
d = {"Event_start": list(event_start_idx),
    "Event_end": list(event_end_idx),
    "Event_start_time": list(event_start),
    "Event_end_time": list(event_end)}
event_list = pd.DataFrame(d)
event_list["DGT"] = dgt
event_list["cell"] = j
event_list["db_name"] = file.name
```

**The Problem**:
- If the lists have different lengths, pandas will align them with NaN
- When broadcasting scalar values (`dgt`, `j`, `file.name`), this could create extra rows
- **Highly unlikely but possible**: A quirk in older pandas versions

## Investigation Results

### Test 1: State Machine Logic ✓ PASSED
- Ran `debug_duplicates.py` on `20240711_dgt2.db`, cell 4
- State machine correctly detected: 139 ON transitions, 139 OFF transitions
- Resulting DataFrame: 139 rows (NO duplicates)
- **Conclusion**: Duplicates NOT created during state machine processing

### Test 2: to_sql Operation ✓ PASSED
- Ran `test_to_sql_duplication.py`
- Confirmed pandas to_sql with `if_exists='append'` works correctly
- No automatic duplication occurs

### Test 3: Database Structure Analysis
- **Rowid Pattern**:
  - 2024 data: rowids 10849-52254 (41,406 rows total)
  - First 20,703 rows: rowids 10849-31551
  - Next  20,703 rows: rowids 31552-52254
  - **NO GAP** - consecutive rowids, suggesting SINGLE database session

- **RowID offset between duplicates**: Exactly 15,919 for EVERY duplicate pair
  - Example: Event at rowid 30192 duplicated at 46111 (gap of 15,919)
  - This offset is consistent across ALL file/cell combinations

- **2023 vs 2024**:
  - 2023 (10,848 rows): All unique, no duplicates
  - 2024 (41,406 rows): All duplicated in single run
  - 2025: Mixed pattern (different issue)

### Test 4: Glob/File Pattern Check
- 204 unique files processed for 2024
- File count matches expected (pairs of dgt1/dgt2 files per date)
- No evidence of files being processed twice

### Key Finding
**The duplicates appear DURING a SINGLE database write session** (consecutive rowids with NO gap). This means:
- NOT caused by multiple script runs
- NOT caused by re-processing existing database
- NOT caused by to_sql quirks
- Something within the SINGLE execution created 20,703 additional rows

## Root Cause Hypothesis (Updated)

The consistent rowid offset of **15,919** between duplicate pairs is significant:
- 15,919 × 2 ≈ 31,838 rows written
- Total 2024 rows = 41,406
- These numbers don't directly correspond to known values

**Possible mechanisms**:
1. **Loop variable issue**: Despite code appearing correct, `j` might be getting reset or `while j <= 4` might execute more than 4 times
2. **File globbing**: Path.rglob() might be returning 2024 files twice (shadow copies? network shares?)
3. **DataFrame operation side-effect**: Broadcasting or internal pandas operation creating duplicates silently
4. **Index corruption**: The `"index"` column being all 0s suggests index handling issue
