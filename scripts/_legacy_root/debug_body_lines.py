"""debug_body_lines.py — debug renderer 内部 body_lines 划分"""
import sys
sys.path.insert(0, '.')
import os
os.environ['DEBUG_SIGNATURE'] = '1'

from core.render import docx_renderer
# 给 _is_signature_or_date_paragraph 加 print
_orig = docx_renderer._is_signature_or_date_paragraph
def debug_check(text, position_in_doc=1.0):
    result = _orig(text, position_in_doc=position_in_doc)
    print(f'  pos={position_in_doc:.2f} | text={text[:30]!r:<30} | signature={result}')
    return result
docx_renderer._is_signature_or_date_paragraph = debug_check

# 重跑生成
import subprocess
subprocess.run(['python', 'regenerate_retrial.py'], cwd='D:\\codex\\V18', check=False)
