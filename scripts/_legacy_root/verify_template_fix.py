"""verify_template_fix.py — 验证两处修复(风险章节删除 + 案号双括号)"""
import sys
sys.path.insert(0, '.')
sys.dont_write_bytecode = True

from core.pipeline.step7_render import _build_retrial_application_text
s7_func = _build_retrial_application_text

# 构造一个 minimal fact_card 和 strategy_card 来调 _build_retrial_application_text
from core.fact_card import FactCard, StrategyCard
from dataclasses import dataclass, field
from typing import List as L

@dataclass
class FakeParty:
    role: str = ""
    name: str = ""

# 模拟 ctx / fc
fc = FactCard(
    case_id="(2026)苏0115民初5112号",
    court="江苏省南京市江宁区人民法院",
    parties=[
        FakeParty(role="原告", name="郑恢快"),
        FakeParty(role="被告", name="江宁区全至惠百货超市店"),
    ],
    key_facts=["判决书落款日期'二〇一六年五月十四日'与案号(2026)矛盾"],
    conflicts=["判决书日期与案号年份不一致"],
    identity="被诉方（被告）",
    amount="23.8元",
)

sc = StrategyCard(
    sabcd_rating="C",
    situation_assessment="对被告有利,但判决书存在程序性瑕疵",
    risk_warnings=[
        "再审申请被驳回的风险极高",  # 这段不应出现在对外文书
        "申请再审期间不停止执行",
        "被告为个体工商户,可能已停止经营",
    ],
)

user_info = {
    "郑恢快": {
        "gender": "男", "birth": "1992年6月27日",
        "ethnicity": "汉族", "address": "福建省三明市大田县广平镇万筹村191号",
        "id_number": "35042519920627071X", "phone": "____",
    },
    "江宁区全至惠百货超市店": {
        "uscc": "92320115MACGE2GL9N", "operator": "刘宝旺",
        "address": "____",
    },
}

text = s7_func(
    fc=fc,
    identity="被诉方（被告）",
    goal="申请再审",
    user_info=user_info,
    strategy_card=sc,
)

print("=" * 70)
print("【验证 1: '四、风险与再审必要性' 章节是否被删除】")
print("=" * 70)
if "风险与再审必要性" in text:
    print("❌ 仍包含'风险与再审必要性'章节!")
    line_no = 0
    for line in text.split('\n'):
        line_no += 1
        if "风险与再审必要性" in line:
            print(f"  在第 {line_no} 行: {line[:80]}")
else:
    print("✅ 已删除'四、风险与再审必要性'章节")

print()
print("=" * 70)
print("【验证 2: 禁用词是否被清除】")
print("=" * 70)
banned = ["风险极高", "可能已停止经营", "即使胜诉也可能无法", "难度较大"]
for b in banned:
    if b in text:
        print(f"  ❌ 含禁用词「{b}」")
    else:
        print(f"  ✅ 不含禁用词「{b}」")

print()
print("=" * 70)
print("【验证 3: 案号是否单括号(无双括号)】")
print("=" * 70)
import re
# 找出案号附近的上下文
for m in re.finditer(r'\(*\(?\d{4}\)?\)?\s*[\)）]?', text):
    pass
# 直接找案号
double_paren = text.count("((2026)")
single_paren_correct = text.count("(2026)")
print(f"  ((2026) 出现次数: {double_paren}")
print(f"  (2026)  出现次数(应该 = 1): {single_paren_correct}")
if double_paren == 0 and single_paren_correct >= 1:
    print("  ✅ 案号无双括号(已修复)")
else:
    print("  ❌ 案号格式异常")

print()
print("=" * 70)
print("【全文预览(关键章节)】")
print("=" * 70)
# 打印事实与理由章节
for sec_name in ["再审请求", "再审事由", "法律依据", "事实与理由", "证据清单", "结论", "此致"]:
    if sec_name in text:
        idx = text.index(sec_name)
        print(f"\n--- {sec_name} ---")
        print(text[idx:idx+300])
