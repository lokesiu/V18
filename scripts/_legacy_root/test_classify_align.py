"""test_classify_align.py — 验证新分类函数"""
import sys
sys.path.insert(0, '.')
from core.render.docx_renderer import _classify_signature_or_date_paragraph

tests = [
    # (text, seen_cizhi, expected_align, label)
    ("此致", False, "left", "此致段(锚点)"),
    ("江苏省南京市中级人民法院", False, "left", "法院名致敬行"),
    ("再审申请人:郑恢快", False, "", "首部再审申请人(seen_cizhi=False)"),
    ("再审申请人:郑恢快", True, "right", "文末再审申请人(seen_cizhi=True)"),
    ("经营者:刘宝旺", False, "", "首部经营者(seen_cizhi=False)"),
    ("经营者:刘宝旺", True, "right", "文末经营者(seen_cizhi=True)"),
    ("(亲笔签名)", False, "right", "签名标记"),
    ("(加盖单位印章)", False, "right", "印章标记"),
    ("____年____月____日", False, "right", "日期占位"),
    ("再审请求:", False, "", "普通正文"),
    ("证据清单:", False, "", "普通章节"),
    ("事实与理由:", False, "", "普通章节"),
]

print(f"{'文本':<40} {'expect':<8} {'actual':<8} {'PASS':<5}")
print("=" * 70)
all_pass = True
for text, seen, expected, label in tests:
    actual = _classify_signature_or_date_paragraph(text, seen_cizhi=seen)
    pass_ = "PASS" if actual == expected else "FAIL"
    if actual != expected:
        all_pass = False
    print(f"{text:<40} {expected or 'None':<8} {actual or 'None':<8} {pass_}")

print()
print("✅ 全部通过" if all_pass else "❌ 有失败")
