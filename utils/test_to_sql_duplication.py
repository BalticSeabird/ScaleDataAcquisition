#!/usr/bin/env python3
"""
Test if pd.DataFrame.to_sql is duplicating rows.
"""
import pandas as pd
import sqlite3
import os

# Create a test database
test_db = "test_duplicate_check.db"
if os.path.exists(test_db):
    os.remove(test_db)

con = sqlite3.connect(test_db)

# Create a simple DataFrame with 5 rows
df_test = pd.DataFrame({
    'value': [1, 2, 3, 4, 5],
    'name': ['a', 'b', 'c', 'd', 'e']
})

print("Original DataFrame:")
print(df_test)
print(f"\nDataFrame shape: {df_test.shape}")
print(f"DataFrame index: {list(df_test.index)}")

# Write to SQL with append
print("\nWriting to SQL (append mode)...")
df_test.to_sql('test_table', con, if_exists='append', index=True)

# Read back from SQL
result = pd.read_sql_query("SELECT * FROM test_table", con)
print(f"\nRow count in ResultSQL: {len(result)}")
print("Rows from SQL:")
print(result)

# Write the same DataFrame again
print("\nWriting to SQL again (append mode)...")
df_test.to_sql('test_table', con, if_exists='append', index=True)

result2 = pd.read_sql_query("SELECT * FROM test_table", con)
print(f"\nRow count in SQL after second write: {len(result2)}")
print("Rows from SQL:")
print(result2)

con.close()
os.remove(test_db)
print("\nTest complete. If duplicates appeared, the to_sql operation has an issue.")
