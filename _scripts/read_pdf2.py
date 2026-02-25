import sys
import os

output_file = os.path.join(os.path.dirname(__file__), 'pdf_result.txt')

try:
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("Starting...\n")
        out.flush()

        try:
            import fitz
            out.write(f"fitz version: {fitz.__version__}\n")
            out.flush()
        except ImportError as e:
            out.write(f"fitz import failed: {e}\n")
            # Try PyMuPDF
            try:
                import pymupdf as fitz
                out.write(f"pymupdf version: {fitz.__version__}\n")
            except ImportError as e2:
                out.write(f"pymupdf import also failed: {e2}\n")
                out.write("Trying pip list...\n")
                import subprocess
                result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True)
                out.write(result.stdout[:2000])
                sys.exit(1)

        pdf_path = r'D:\오아시스\SANCHUL_Sheet_1\설명서\egManual.pdf'
        out.write(f"Opening: {pdf_path}\n")
        out.write(f"File exists: {os.path.exists(pdf_path)}\n")
        out.write(f"File size: {os.path.getsize(pdf_path)}\n")
        out.flush()

        doc = fitz.open(pdf_path)
        out.write(f"Total pages: {doc.page_count}\n")
        out.flush()

        # Search for relevant sections
        keywords = ['일위대가', '산출', '일위표', '조각', '블럭', '복사', '이동', '붙이기', '단축키', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11']

        found_pages = {}
        for i in range(doc.page_count):
            page = doc[i]
            text = page.get_text()
            matched = []
            for kw in keywords:
                if kw in text:
                    matched.append(kw)
            if matched:
                found_pages[i] = matched

        out.write(f"\nFound {len(found_pages)} relevant pages\n")
        for pg, kws in sorted(found_pages.items()):
            out.write(f"  Page {pg+1}: {', '.join(kws)}\n")
        out.flush()

        # Extract text from found pages
        for i in sorted(found_pages.keys()):
            page = doc[i]
            text = page.get_text()
            out.write(f"\n{'='*60}\n")
            out.write(f"=== PAGE {i+1} (keywords: {', '.join(found_pages[i])}) ===\n")
            out.write(f"{'='*60}\n")
            out.write(text)
            out.write("\n")
            out.flush()

        out.write("\nDONE.\n")

except Exception as e:
    import traceback
    with open(output_file, 'a', encoding='utf-8') as out:
        out.write(f"\nERROR: {e}\n")
        out.write(traceback.format_exc())
