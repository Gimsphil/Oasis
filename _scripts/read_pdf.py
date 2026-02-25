import sys
import fitz

doc = fitz.open(r'D:\오아시스\SANCHUL_Sheet_1\설명서\egManual.pdf')
print(f'Total pages: {doc.page_count}', flush=True)

# Search for relevant sections
keywords = ['일위대가', '산출', '일위표', '조각', '블럭', '복사', '이동', '붙이기']

found_pages = set()
for i in range(doc.page_count):
    page = doc[i]
    text = page.get_text()
    for kw in keywords:
        if kw in text:
            found_pages.add(i)
            break

print(f'Found relevant pages: {sorted(found_pages)}', flush=True)

# Extract text from relevant pages
for i in sorted(found_pages):
    page = doc[i]
    text = page.get_text()
    print(f'\n=== PAGE {i+1} ===', flush=True)
    print(text[:3000], flush=True)

# Also extract first 3 pages for context
print('\n\n=== FIRST 3 PAGES (CONTEXT) ===', flush=True)
for i in range(min(3, doc.page_count)):
    if i not in found_pages:
        page = doc[i]
        text = page.get_text()
        print(f'\n=== PAGE {i+1} ===', flush=True)
        print(text[:2000], flush=True)
