"""
Add quality mark (1-4) as a new field in Events23-25_weights.db.

Quality mark hierarchy:
  1 = AGGRESSIVE (highest quality)
  2 = RECOMMENDED (balanced)
  3 = LENIENT (maximum volume)
  4 = REJECTED (always bad)
"""

import sqlite3
import pandas as pd
from pathlib import Path

db_path = Path("out/Events23-25_weights.db")

print("Loading database...")
con = sqlite3.connect(db_path)
df = pd.read_sql_query('SELECT * FROM event', con)
con.close()

print(f"Loaded {len(df)} events")

# Assign quality marks based on existing boolean columns
def assign_quality_mark(row):
    if row['passes_aggressive']:
        return 1
    elif row['passes_moderate']:
        return 2
    elif row['passes_lenient']:
        return 3
    else:
        return 4

print("Assigning quality marks...")
df['quality_mark'] = df.apply(assign_quality_mark, axis=1)

# Count distribution
distribution = df['quality_mark'].value_counts().sort_index()
print("\nQuality mark distribution:")
for mark, count in distribution.items():
    pct = 100 * count / len(df)
    labels = {1: "AGGRESSIVE", 2: "RECOMMENDED", 3: "LENIENT", 4: "REJECTED"}
    print(f"  Mark {mark} ({labels[mark]:12}): {count:6} events ({pct:5.1f}%)")

# Save back to database
print("\nSaving to database...")
con = sqlite3.connect(db_path)
df.to_sql('event', con, if_exists='replace', index=False)
con.close()

print("✓ Quality marks added successfully!")
print(f"\nDatabase: {db_path}")
print(f"New column: quality_mark (values: 1-4)")
