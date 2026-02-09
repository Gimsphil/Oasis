import sys
import os

out_path = r'D:\오아시스\SANCHUL_Sheet_1\_scripts\simple_out.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(f"Python: {sys.version}\n")
    f.write(f"Executable: {sys.executable}\n")
    try:
        import fitz
        f.write(f"fitz: {fitz.__version__}\n")
    except:
        f.write("fitz not available\n")
        try:
            import pymupdf
            f.write(f"pymupdf: {pymupdf.__version__}\n")
        except:
            f.write("pymupdf not available\n")

    pdf_path = r'D:\오아시스\SANCHUL_Sheet_1\설명서\egManual.pdf'
    f.write(f"PDF exists: {os.path.exists(pdf_path)}\n")
    if os.path.exists(pdf_path):
        f.write(f"PDF size: {os.path.getsize(pdf_path)} bytes\n")
