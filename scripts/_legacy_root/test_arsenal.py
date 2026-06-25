"""test_arsenal.py"""
import sys; sys.path.insert(0, '.')
sys.dont_write_bytecode = True
from core.attack_arsenal import (
    detect_case_types, match_arsenal, compute_lethality_score,
    get_style_instructions, get_arsenal_context, ARSENAL,
)
from collections import Counter

test_text = "原告李达与被告程颖颖签订《垫资协议》和《居间合同》,被告支付了20万元利息及居间费。后因融资失败,原告主张4万元违约金、律师费3000元、差旅费3000元、保函费500元,申请冻结被告56804元财产。"

print("=== 案由识别 ===")
print(detect_case_types(test_text))
print()
print("=== 论点匹配 ===")
match = match_arsenal(test_text)
for p in match.available_points:
    print(f"  - {p.title} (杀伤力 {p.lethality}/5)")
print()
print("=== 杀伤力指数 ===")
print(f"  原始事实文本: {compute_lethality_score(test_text)}/100")
sample = "原告系职业放贷人,主张的违约金过高,应当按LPR予以调减。律师费、差旅费不应由被告承担。超标的保全应当赔偿。恶意诉讼。"
print(f"  含攻击性关键词: {compute_lethality_score(sample)}/100")
print()
print("=== 论点库容量 ===")
print(f"  总论点: {len(ARSENAL)} 个")
c = Counter(p.category for p in ARSENAL)
for cat, n in c.most_common():
    print(f"    {cat}: {n}")
print()
print("=== 风格 prompt 注入(sharp 前 200 字) ===")
print(get_style_instructions("sharp")[:200])
