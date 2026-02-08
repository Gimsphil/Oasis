import sqlite3
import os
import sys

# Windows console encoding fix
sys.stdout.reconfigure(encoding='utf-8')

db_paths = [
    r"D:\이지맥스\data\자료사전.db",
    r"D:\이지맥스\산출목록\조명기구타입.db"
]

output_file = "schema_info.txt"

def inspect_db():
    with open(output_file, "w", encoding="utf-8") as f:
        for path in db_paths:
            f.write(f"--- Inspecting: {path} ---\n")
            if not os.path.exists(path):
                f.write("File not found.\n")
                continue

            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                
                # List tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    f.write(f"\nTable: [{table_name}]\n")
                    
                    # List columns
                    cursor.execute(f"PRAGMA table_info([{table_name}])")
                    columns = cursor.fetchall()
                    # (cid, name, type, notnull, dflt_value, pk)
                    col_names = [col[1] for col in columns]
                    f.write(f"  Columns: {col_names}\n")
                    
                    # Sample data
                    cursor.execute(f"SELECT * FROM [{table_name}] LIMIT 1")
                    row = cursor.fetchone()
                    f.write(f"  Sample: {row}\n")
                    
                conn.close()
            except Exception as e:
                f.write(f"Error: {e}\n")

if __name__ == "__main__":
    inspect_db()
    print(f"Schema info written to {output_file}")
