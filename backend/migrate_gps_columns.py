"""
Migration: Add GPS latitude/longitude columns to attendance table.
Run once: uv run migrate_gps_columns.py
"""
import psycopg2
from app.core.config import settings

conn = psycopg2.connect(settings.DATABASE_URL)
cur  = conn.cursor()

columns = [
    ("latitude",           "DOUBLE PRECISION"),
    ("longitude",          "DOUBLE PRECISION"),
    ("checkout_latitude",  "DOUBLE PRECISION"),
    ("checkout_longitude", "DOUBLE PRECISION"),
]

for col, col_type in columns:
    cur.execute(f"""
        ALTER TABLE attendance
        ADD COLUMN IF NOT EXISTS {col} {col_type};
    """)
    print(f"  OK: {col} ({col_type})")

conn.commit()
cur.close()
conn.close()
print("Migration complete.")
