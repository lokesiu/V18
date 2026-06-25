"""debug_classify2.py"""
import sys; sys.path.insert(0, '.')
sys.dont_write_bytecode = True
import importlib
from core.render import docx_renderer
importlib.reload(docx_renderer)
fn = docx_renderer._classify_signature_or_date_paragraph

tests = [
    ('答辩人:程颖颖', True),
    ('答辩人：程颖颖', True),  # 全角冒号
    ('答辩人程颖颖', True),
    ('被答辩人:李林', True),
    ('原告:张三', True),
    ('具状人:某某', True),
]
for t, s in tests:
    print(f'text={t!r:<30} seen={s} result={fn(t, s)!r}')
