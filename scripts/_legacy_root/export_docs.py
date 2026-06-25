"""把所有 docx 导出为 utf-8 markdown 文件方便阅读."""
from pathlib import Path
from docx import Document

out_dir = Path(r'D:\codex\V18\test_run\output\customer')
md_dir = Path(r'D:\codex\V18\test_run\md')
md_dir.mkdir(exist_ok=True)

for p in sorted(out_dir.glob('*.docx')):
    doc = Document(str(p))
    paras = [pp.text for pp in doc.paragraphs if pp.text.strip()]
    md = f'# {p.stem}\n\n'
    for line in paras:
        md += line + '\n\n'
    out = md_dir / (p.stem + '.md')
    out.write_text(md, encoding='utf-8')
    print(f'Wrote: {out.name}  ({len(paras)} paras, {len(md)} chars)')
print(f'\nAll in: {md_dir}')