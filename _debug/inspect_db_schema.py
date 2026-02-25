import sqlite3
import os

db_paths = [
    r"D:\이지맥스\data\자료사전.db",
    r"D:\이지맥스\산출목록\조명기구타입.db"
]

def inspect_db(path):
    print(f"--- Inspecting: {path} ---")
    if not os.path.exists(path):
        print("File not found.")
        return

    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # List tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"\nTable: [{table_name}]")
            
            # List columns
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            print(f"  Columns: {col_names}")
            
            # Sample data
            cursor.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
            row = cursor.fetchone()
            print(f"  Sample: {row}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    for p in db_paths:
        inspect_db(p)
