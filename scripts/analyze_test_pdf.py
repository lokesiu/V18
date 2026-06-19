"""Analyze test PDF title position."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\codex\V18')
import pdfplumber

# Create test PDF if needed
pdf_path = r'D:\codex\V18\outputs\case_20260618_135333_88c606\customer\01_test.pdf'
if not os.path.exists(pdf_path):
    from core.render.pdf_converter import _try_reportlab
    docx_path = r'D:\codex\V18\outputs\case_20260618_135333_88c606\customer\01_案件处境评估报告_程颖颖案.docx'
    _try_reportlab(docx_path, pdf_path)

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    
    print('First 5 words with positions:')
    for i, w in enumerate(words[:5]):
        print(f'  {i+1}. "{w["text"]}" at x0={w["x0"]:.1f}, top={w["top"]:.1f}')
    
    page_center = page.width / 2
    print(f'\nPage center: {page_center:.1f}')
    
    if words:
        first_line_top = words[0]['top']
        first_line_words = [w for w in words if abs(w['top'] - first_line_top) < 5]
        if first_line_words:
            line_start = min(w['x0'] for w in first_line_words)
            line_end = max(w['x1'] for w in first_line_words)
            line_center = (line_start + line_end) / 2
            print(f'First line: x0={line_start:.1f}, x1={line_end:.1f}, center={line_center:.1f}')
            print(f'Offset from page center: {line_center - page_center:.1f}')
