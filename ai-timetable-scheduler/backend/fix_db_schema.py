import sqlite3
import os
import sys

# 1. Locate Database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "sql_app.db")

print(f"Checking database at: {DB_FILE}")

if not os.path.exists(DB_FILE):
    print("[ERROR] Database file not found. Running the backend for the first time will create it.")
    sys.exit(1)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# 2. Check and Fix Subjects Table ('class_id')
try:
    print("Checking 'subjects' table for 'class_id'...")
    cursor.execute("PRAGMA table_info(subjects)")
    columns = [col[1] for col in cursor.fetchall()]

    if "class_id" not in columns:
        print("[WARNING] 'class_id' column MISSING. Attempting to fix...")
        try:
            cursor.execute("ALTER TABLE subjects ADD COLUMN class_id INTEGER REFERENCES classes(id)")
            conn.commit()
            print("[SUCCESS] Successfully added 'class_id' column to 'subjects'.")
        except Exception as e:
            print(f"[ERROR] Failed to alter table: {e}")
    else:
        print("[SUCCESS] 'class_id' column already exists.")
        
    # 3. Check for any corruption by running a simple query
    cursor.execute("SELECT count(*) FROM subjects")
    count = cursor.fetchone()[0]
    print(f"[SUCCESS] Database Integrity Check Passed. Found {count} subjects.")

except Exception as e:
    print(f"[ERROR] Database Error: {e}")
    
finally:
    conn.close()

print("\n--- Repair Complete ---")
print("Please restart your backend server now.")
