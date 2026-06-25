"""regen_chengying_render.py — 只重渲染,不重跑 LLM"""
import sys
sys.path.insert(0, '.')
sys.dont_write_bytecode = True
import os
import shutil

from core.render.docx_renderer import render_docx_from_text
from core.render.pdf_converter import convert_to_pdf

# 读答辩状原文
with open(r'D:\codex\V18\test_run_judgment\程颖_答辩状.md', 'r', encoding='utf-8') as f:
    raw = f.read()
content = raw.split('\n', 1)[1].strip() if raw.startswith('#') else raw

# 渲染
docx_out = r'D:\codex\V18\test_run_judgment\output_程颖\customer\06_答辩状_程颖颖案.docx'
render_docx_from_text(content, docx_out, title='')
print(f'DOCX: {os.path.getsize(docx_out)} bytes')

pdf_out = docx_out.replace('.docx', '.pdf')
ok = convert_to_pdf(docx_out, pdf_out)
print(f'PDF: {ok} ({os.path.getsize(pdf_out) if os.path.exists(pdf_out) else 0} bytes)')

# 复制到桌面
shutil.copyfile(pdf_out, r'C:\Users\哆哆\Desktop\程颖_答辩状_v2.pdf')
print(f'桌面副本: C:\\Users\\哆哆\\Desktop\\程颖_答辩状_v2.pdf')

# 验证 alignment
from docx import Document
doc = Document(docx_out)
print()
print('=== 文末段落 alignment ===')
for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    if not text:
        continue
    if any(kw in text for kw in ['此致', '赣州', '答辩人', '____']):
        align = p.alignment
        align_name = {None: 'default', 0: 'LEFT', 1: 'CENTER', 2: 'RIGHT', 3: 'JUSTIFY'}.get(align, str(align))
        marker = '✅' if align_name in ('LEFT', 'RIGHT') else '⚠️'
        print(f'{marker} [{i:2}] [{align_name:<8}] {text[:60]}')
