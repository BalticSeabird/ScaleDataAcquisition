# Duplicate Entry Investigation  - FINAL REPORT

## Executive Summary
**Every unique event recorded for 2024 appears exactly TWICE in the database**, while 2023 data has no duplicates. The root cause appears to be that **the while loop is executing 8 times instead of 4 times per file**, or **the glob pattern is matching files twice**.

## Key Findings

### Data Structure
- 41,406 total rows for 2024 = 20,703 unique events × 2
- Database written in SINGLE session (consecutive rowids 10849-52254)
- Each file/cell combination appears exactly twice
- Same data, same order, completely duplicated

### What's NOT the Problem ✓ (Tested & Confirmed)
1. **State machine logic**: Correctly detects 139 unique events (no duplicates)
2. **DataFrame creation**: Produces correct number of rows (not doubled)
3. **Pandas to_sql operation**: Works correctly with `if_exists='append'`
4. **File matching**: 204 files matched, all processed
5. **Multiple script runs**: Single database session (no gaps in rowids)

### What COULD Be the Problem ⚠️

**HYPOTHESIS 1**: Loop logic error (MOST LIKELY)
- Code appears correct: `while j <= 4: ... j += 1`
- But something could cause it to run 8 times or files to be processed twice
- Cannot explain from code review alone

**HYPOTHESIS 2**: Glob pattern returns files twice
- `Path.rglob("*.db")` might iterate twice somehow
- Unlikely but possible if there are symlinks or volume mounts

**HYPOTHESIS 3**: Numpy/Pandas silent duplication
- `np.concat()` or boolean indexing might be duplicating data under specific conditions
- Has NOT been observed in isolated tests

**HYPOTHESIS 4**: Database-level issue
- SQLite or pandas-sql might have special behavior with index columns
- All duplicates have `index = 0` (suspicious)

## Diagnostic Output Structure

The data shows:
- First batch (rowids 10849-31551): 20,703 events
  - Files ordered: dgt1 chronologically, then dgt2
  - 103 dgt1 files, 101 dgt2 files

- Second batch (rowids 31552-52254): identical 20,703 events
  - Same file/cell combinations
  - Same order as first batch

## Recommended Next Steps

1. **Add detailed logging to script**
   ```python
   print(f"Processing file: {file.name}")
   print(f"  j starts at: {j}")
   for j in while j <= 4:
       print(f"    Cell {j}: {len(event_list)} events before to_sql")
       event_list.to_sql(...)
       print(f"    Cell {j}: written to DB")
   ```

2. **Run script with test data**
   - Process just 1-2 files to see if duplicates appear
   - Check if each cell is being processed once or twice

3. **Check for modifications during execution**
   - Verify script file doesn't change while running
   - Check if there are multiple script instances

4. **Verify glob behavior**
   - Print all files as they're discovered
   - Count files before and after processing

## Files Involved
- Script: `/home/jonas/Documents/vscode/ScaleDataAcquisition/utils/step1_state_machine_fast.py`
- Output DB: `/home/jonas/Documents/vscode/ScaleDataAcquisition/out/Events23-25.db`
- Source DBs: `/mnt/BSP_NAS2/Other_sensors/weightlog/*.db`

## Impact

The 2024 data in the Events database contains:
- 41,406 rows for 2024 (should be ~20,700)
- Every event appears twice
- This will affect all downstream analysis

**Recommendation**: Regenerate the Events database by:
1. Identifying and fixing the duplication bug
2. Re-running just on 2024 data to create clean output
3. Verifying 2023 and 2025 are also correct
