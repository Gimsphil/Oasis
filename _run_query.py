import sqlite3, os
result_path = os.path.join(os.getcwd(), "query_result.txt")
with open(result_path, "w", encoding="utf-8") as f:
    f.write("TEST LINE\n")
    f.flush()
    os.fsync(f.fileno())
