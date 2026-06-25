"""test_signature_align.py — 验证签名/日期/此致段被识别为右下角"""
import sys
sys.path.insert(0, '.')
sys.dont_write_bytecode = True

from core.render.docx_renderer import _is_signature_or_date_paragraph

tests = [
    ("此致", True),
    ("江苏省南京市中级人民法院", True),
    ("再审申请人:郑恢快", True),
    ("经营者:刘宝旺", True),
    ("(亲笔签名)", True),
    ("(签名)", True),
    ("(加盖单位印章)", True),
    ("____年____月____日", True),
    ("答辩人:某某公司", True),
    ("原告:张三", True),
    # 不该识别的:
    ("再审请求:", False),
    ("证据清单:", False),
    ("事实与理由:", False),
    ("一、案号矛盾", False),
    ("本判决为终审判决", False),
]

print(f"{'文本':<40} {'期望':<6} {'实际':<6} {'结果'}")
print("=" * 70)
all_pass = True
for text, expected in tests:
    actual = _is_signature_or_date_paragraph(text)
    result = "PASS" if actual == expected else "FAIL"
    if actual != expected:
        all_pass = False
    print(f"{text:<40} {str(expected):<6} {str(actual):<6} {result}")

print()
print("✅ 全部通过" if all_pass else "❌ 有失败用例")
