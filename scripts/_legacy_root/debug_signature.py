"""debug_signature.py"""
import sys
sys.path.insert(0, '.')
from core.render.docx_renderer import _is_signature_or_date_paragraph

text = '再审申请人:郑恢快'
print(f'text repr: {text!r}')
print(f'text len: {len(text)}')
print(f'startswith 冒号: {text.startswith(chr(0x003A).join(["再审申请人", ""]))}')
# 测试不同位置
for pos in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]:
    print(f'pos={pos}: {_is_signature_or_date_paragraph(text, position_in_doc=pos)}')

# 也测试 经营者
print()
text2 = '经营者:刘宝旺'
print(f'经营者 text repr: {text2!r}')
for pos in [0.05, 0.1, 0.5, 0.7, 0.9]:
    print(f'pos={pos}: {_is_signature_or_date_paragraph(text2, position_in_doc=pos)}')
