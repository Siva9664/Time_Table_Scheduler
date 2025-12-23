import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql_app.db")

def check_db():
    if not os.path.exists(DB_FILE):
        print(f"❌ Database file '{DB_FILE}' not found. Please run the backend server to create it.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check Subject table
        cursor.execute("PRAGMA table_info(subjects)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("Subjects table columns:", column_names)
        
        if "class_id" in column_names:
            print("✅ 'class_id' column FOUND in 'subjects' table.")
        else:
            print("❌ 'class_id' column MISSING. Please delete sql_app.db and restart backend.")

        # Check Faculty table
        cursor.execute("PRAGMA table_info(faculty)")
        f_cols = [c[1] for c in cursor.fetchall()]
        print("Faculty table columns:", f_cols)
        
        conn.close()
    except Exception as e:
        print(f"❌ Error checking DB: {e}")

if __name__ == "__main__":
    print(f"Checking {os.path.abspath(DB_FILE)}...")
    check_db()
