"""regen_chengying_clean.py — 清洗答辩状里 LLM 编造的当事人信息 + 重渲染"""
import sys
sys.path.insert(0, '.')
sys.dont_write_bytecode = True
import os
import re
import shutil

from core.render.docx_renderer import render_docx_from_text
from core.render.pdf_converter import convert_to_pdf

# 读原答辩状
with open(r'D:\codex\V18\test_run_judgment\程颖_答辩状.md', 'r', encoding='utf-8') as f:
    raw = f.read()
content = raw.split('\n', 1)[1].strip() if raw.startswith('#') else raw

# 1. 清洗被答辩人段(LLM 编造的内容)
# 模式:被答辩人(原告):XXX,女/男,XXXX年XX月XX日出生,住址...,身份证号...,电话...
# → 被答辩人(原告):XXX,性别____,____年____月____日出生,住址____,身份证号____,电话____
def clean_defendant_paragraph(text):
    if not text.startswith("被答辩人"):
        return text
    # 拆前缀(被答辩人(原告):XXX) + 剩余
    m = re.match(r'^(被答辩人[（(]原告[）)][:：]\s*[^\s,，]+)(.*)$', text)
    if not m:
        return text
    head = m.group(1)
    # 剩余部分全部替换为标准占位
    placeholder = ",性别____,____年____月____日出生,民族____,住址____,身份证号____,联系电话____"
    return head + placeholder

lines = content.split('\n')
cleaned_lines = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith("被答辩人（原告）") or stripped.startswith("被答辩人(原告)"):
        line = clean_defendant_paragraph(stripped)
    cleaned_lines.append(line)
content_cleaned = '\n'.join(cleaned_lines)

# 2. 写回 markdown
md_path = r'D:\codex\V18\test_run_judgment\程颖_答辩状_clean.md'
with open(md_path, 'w', encoding='utf-8') as f:
    f.write('# 民事答辩状(程颖颖案)\n\n')
    f.write(content_cleaned)
print(f'Markdown: {md_path}')

# 3. 重渲染
docx_out = r'D:\codex\V18\test_run_judgment\output_程颖\customer\06_答辩状_程颖颖案.docx'
render_docx_from_text(content_cleaned, docx_out, title='')
print(f'DOCX: {os.path.getsize(docx_out)} bytes')

pdf_out = docx_out.replace('.docx', '.pdf')
ok = convert_to_pdf(docx_out, pdf_out)
print(f'PDF: {ok} ({os.path.getsize(pdf_out) if os.path.exists(pdf_out) else 0} bytes)')

# 4. 复制到桌面
shutil.copyfile(pdf_out, r'C:\Users\哆哆\Desktop\程颖_答辩状_clean.pdf')
print(f'桌面副本: C:\\Users\\哆哆\\Desktop\\程颖_答辩状_clean.pdf')

# 5. 验证被答辩人段
print()
print('=== 清洗后被答辩人段 ===')
for line in content_cleaned.split('\n'):
    if line.startswith('被答辩人'):
        print(f'  {line}')
