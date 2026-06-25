"""读 docx 内容."""
import sys
from pathlib import Path
from docx import Document

out = Path(r'D:\codex\V18\test_run\output\customer')
files = sorted(out.glob('*.docx'))
print(f'Found {len(files)} docx files', file=sys.stderr)

for p in files:
    try:
        doc = Document(str(p))
        paras = [pp.text for pp in doc.paragraphs if pp.text.strip()]
        print(f'\n===== {p.name} =====', file=sys.stderr)
        print(f'  ({len(paras)} paragraphs)', file=sys.stderr)
        for i, line in enumerate(paras[:12]):
            line_short = line[:100] + '...' if len(line) > 100 else line
            print(f'  [{i:2d}] {line_short}', file=sys.stderr)
    except Exception as e:
        print(f'Error reading {p.name}: {e}', file=sys.stderr)
sys.stderr.flush()