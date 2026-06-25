"""extract_pdf_text.py — 从最新 PDF 抽取文本验证"""
import sys
sys.path.insert(0, '.')
sys.dont_write_bytecode = True

# 用 python-docx 读最新 DOCX (比 PDF 易读)
from docx import Document
import os

docx_path = r"D:\codex\V18\test_run_judgment\output_v3\customer\06_再审申请书_江宁区全至惠百货超市店案.docx"
doc = Document(docx_path)
full_text = "\n".join([p.text for p in doc.paragraphs])
print(f"DOCX 总字符数: {len(full_text)}")
print()
print("=" * 70)
print("【完整正文】")
print("=" * 70)
print(full_text)

# 写一份 markdown 副本
md_path = r"D:\codex\V18\test_run_judgment\再审申请书_v3_打磨版.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write("# 民事再审申请书(打磨版 v3.1)\n\n")
    f.write(full_text)
print(f"\nMarkdown 已写入: {md_path}")
