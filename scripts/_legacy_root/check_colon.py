"""check_colon.py"""
text = '再审申请人:郑恢快'
print(f'len: {len(text)}')
print(f'char at 5: {text[5]!r} U+{ord(text[5]):04X}')
# 半角冒号 :
print(f'startswith 半角冒号: {text.startswith(chr(0x003A).join(["再审申请人", ""]))}')
# 全角冒号 :
print(f'startswith 全角冒号: {text.startswith(chr(0xFF1A).join(["再审申请人", ""]))}')
# 通用正则匹配
import re
m = re.match(r'再审申请人.', text)
print(f'正则: {m}')
