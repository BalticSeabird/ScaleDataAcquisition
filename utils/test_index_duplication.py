#!/usr/bin/env python3
"""
Debug script to check if DataFrame index=0 + broadcasting could cause duplication
in to_sql append mode.
"""
import pandas as pd
import sqlite3
import os

# Create test database
test_db = "test_index_duplication.db"
if os.path.exists(test_db):
    os.remove(test_db)

con = sqlite3.connect(test_db)

# Scenario 1: What if we create DataFrames with the same index multiple times?
print("=== TEST 1: Multiple to_sql calls with overlapping indices ===")
for iteration in range(1, 3):
    df = pd.DataFrame({
        'value': [100, 200, 300],
        'iteration': [iteration, iteration, iteration]
    })
    print(f"\nIteration {iteration}:")
    print(f"  DataFrame index: {list(df.index)}")
    print(f"  Rows: {len(df)}")
    df.to_sql('test1', con, if_exists='append', index=True)

result = pd.read_sql_query("SELECT * FROM test1", con)
print(f"\nFinal table (test1):")
print(result)
print(f"Total rows: {len(result)}")

# Scenario 2: What if we convert to list then back to DataFrame?
print("\n" + "="*60)
print("=== TEST 2: Convert Series to list, create DataFrame, append ===")
for iteration in range(1, 3):
    series = pd.Series([10, 20, 30])
    list_values = list(series)
    df = pd.DataFrame({'value': list_values, 'iter': iteration})
    print(f"\nIteration {iteration}:")
    print(f"  List: {list_values}")
    print(f"  DataFrame shape: {df.shape}")
    df.to_sql('test2', con, if_exists='append', index=True)

result2 = pd.read_sql_query("SELECT * FROM test2", con)
print(f"\nFinal table (test2):")
print(result2)

con.close()
os.remove(test_db)
print("\n(Test database cleaned up)")
