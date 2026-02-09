import sys, os

output_file = os.path.join(r"D:\오아시스\SANCHUL_Sheet_1", "query_result.txt")

try:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Script started\n")
        
        db_path = r"D:\오아시스\data\자료사전.db"
        if os.path.exists(db_path):
            f.write(f"DB found: {db_path}\n")
        else:
            f.write(f"DB NOT found: {db_path}\n")
            base = r"D:\오아시스"
            for root, dirs, files in os.walk(base):
                for fn in files:
                    if fn.endswith('.db'):
                        f.write(f"  Found DB: {os.path.join(root, fn)}\n")
        
        f.write("Script finished\n")
except Exception as e:
    with open(output_file + ".err", "w") as ef:
        ef.write(str(e))
