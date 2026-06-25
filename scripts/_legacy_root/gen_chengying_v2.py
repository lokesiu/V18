"""gen_chengying_v2.py — 程颖案件 v2 生成(锋芒 + 笑面虎 + 反诉)

直接调用 DeepSeek API 出答辩状(避免重跑整个 pipeline,8+ 分钟),
用 attack_arsenal 的论点 + 风格指令。

输入:output_程颖/_internal/distilled_card.json(已有)
输出:
  - 答辩状_锋芒毕露_v2.pdf / .md
  - 答辩状_笑面虎_v2.pdf / .md
  - 反诉状_超标的保全_v2.pdf / .md
  - 证据补强清单(基于评估报告 + 行动建议书汇总)
"""
import sys
sys.path.insert(0, '.')
sys.dont_write_bytecode = True
import json
import os
import shutil

from core.ai_config import get_ai_config, is_api_configured
from core.attack_arsenal import (
    match_arsenal, get_arsenal_context, get_style_instructions,
    compute_lethality_score,
)
from core.build_counter_claim import build_counter_claim_text
from core.fact_card import FactCard, Party, SourceRef
from core.pipeline.step7_render import _extract_user_info_from_refs
from core.render.docx_renderer import render_docx_from_text
from core.render.pdf_converter import convert_to_pdf

# ── 1. 加载已有 distilled_card ──────────────────────────────────────────

with open(r'D:\codex\V18\test_run_judgment\output_程颖\_internal\distilled_card.json', 'r', encoding='utf-8') as f:
    distilled_data = json.load(f)

fc_data = distilled_data['fact_card']
sc_data = distilled_data.get('strategy_card', {})

# 重建 FactCard
parties = [Party(role=p.get('role', ''), name=p.get('name', ''))
           for p in fc_data.get('parties', [])]
source_refs = [SourceRef(
    file_name=s.get('file_name', ''),
    excerpt=s.get('excerpt', ''),
    page=s.get('page', 0),
) for s in fc_data.get('source_refs', [])]
fc = FactCard(
    case_id=fc_data.get('case_id', ''),
    court=fc_data.get('court', ''),
    parties=parties,
    key_facts=fc_data.get('key_facts', []),
    disputed_facts=fc_data.get('disputed_facts', []),
    conflicts=fc_data.get('conflicts', []),
    missing_materials=fc_data.get('missing_materials', []),
    identity=fc_data.get('identity', '被诉方（被告）'),
    amount=fc_data.get('amount', ''),
    source_refs=source_refs,
)

# 抽取 user_info
user_info = _extract_user_info_from_refs(fc, None)

# ── 2. 构造事实文本(给论点库用) ──────────────────────────────────────────

fact_text_parts = []
fact_text_parts.append(f"案号:{fc.case_id or ''}")
fact_text_parts.append(f"法院:{fc.court or ''}")
if fc.key_facts:
    fact_text_parts.extend(fc.key_facts)
if fc.disputed_facts:
    fact_text_parts.extend(fc.disputed_facts)
fact_text = '\n'.join(fact_text_parts)

print("=" * 70)
print("论点库匹配")
print("=" * 70)
match = match_arsenal(fact_text, counter_party="原告", min_lethality=3)
print(f"识别案由: {match.case_types}")
print(f"可用论点(杀伤力 >= 3): {len(match.available_points)}")
for p in match.available_points[:8]:
    print(f"  - {p.title} (杀伤力 {p.lethality}/5)")

# ── 3. 检查 API ────────────────────────────────────────────────────────

assert is_api_configured(), "DeepSeek API 未配置"

# ── 4. 直接调 DeepSeek 出答辩状 ──────────────────────────────────────────

from core.ai_config import call_deepseek

BASE_PROMPT = """你是一名资深诉讼律师,代理被告(答辩人)出具《民事答辩状》。

【核心原则】
1. 严禁使用"被告认为""原告可能""望贵院酌情"等弱化措辞
2. 严禁编造当事人身份证号/出生日期/住址/电话 — 未提供的字段用 ____
3. 必须引用具体法条(精确到条号)
4. 严禁使用"风险评估""难度较大""可能败诉"等内部意见措辞
5. 答辩状结构:首部+答辩请求+事实与理由+法律依据+结语+签名

【事实摘要】
- 案号:{case_id}
- 法院:{court}
- 我方:程颖颖(被告)
- 对方:李林、李达(原告)
- 案由:合同纠纷(垫资协议+居间合同)
- 已退还本金:20万元(2025年10月11日前全部退还)
- 对方主张:违约金4万+律师费3000+差旅费3000+保函费500
- 保全金额:56,804元(超标的)
- 答辩请求:驳回对方全部诉讼请求 + 反诉对方超额保全损失
"""


def make_user_msg(style: str) -> str:
    arsenal_ctx = get_arsenal_context(fact_text, style=style, counter_party="原告", top_n=6)
    return (
        f"## 案件上下文\n\n"
        f"{BASE_PROMPT.format(case_id=fc.case_id, court=fc.court)}\n\n"
        f"## 详细事实\n\n{fact_text}\n\n"
        f"## 论点库(根据本案事实自动匹配的攻击性论点)\n\n{arsenal_ctx}\n\n"
        f"## 任务\n\n请按【{style}】风格撰写完整的《民事答辩状》,逐项回应原告的诉讼请求,直接亮明论点库中的论点,正面亮明法条依据。"
    )


def call_llm_for_defense(style: str) -> str:
    """调用 DeepSeek 生成答辩状。"""
    print()
    print("=" * 70)
    print(f"调用 DeepSeek 生成答辩状({style}风格)...")
    print("=" * 70)
    style_instr = get_style_instructions(style)
    system_prompt = style_instr + "\n\n" + BASE_PROMPT

    msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": make_user_msg(style)},
    ]
    result = call_deepseek(
        msgs,
        max_tokens=8192,
        temperature=0.4,
        timeout=180,
    )
    if not result['success']:
        print(f"❌ LLM 调用失败: {result['error']}")
        return ""
    print(f"✅ 生成成功 ({len(result['content'])} 字符, {result['latency_ms']}ms)")
    return result['content']


# ── 5. 调用 LLM 生成 2 份答辩状 ──────────────────────────────────────────

defense_sharp = call_llm_for_defense("sharp")
defense_tiger = call_llm_for_defense("tiger")

# ── 6. 渲染 + 保存 ──────────────────────────────────────────────────────

OUT_DIR = r'D:\codex\V18\test_run_judgment\output_程颖\customer'
os.makedirs(OUT_DIR, exist_ok=True)


def render_to_pdf(content: str, doc_type: str, file_base: str) -> str:
    """渲染 DOCX + PDF。返回桌面路径。"""
    docx_path = os.path.join(OUT_DIR, f'{file_base}.docx')
    pdf_path = docx_path.replace('.docx', '.pdf')

    # 先清掉敏感信息(mask_sensitive)
    from core.text_utils import clean_docx_content, mask_sensitive_in_line
    content = clean_docx_content(content)
    lines = content.split('\n')
    content = '\n'.join([mask_sensitive_in_line(l) for l in lines])

    ok = render_docx_from_text(content, docx_path, title=doc_type)
    if ok:
        ok = convert_to_pdf(docx_path, pdf_path)
    return pdf_path if ok and os.path.exists(pdf_path) else ''


# 写 markdown 副本
def write_md(content: str, md_path: str, title: str):
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f'# {title}\n\n')
        f.write(content)


# 答辩状 锋芒毕露
md_sharp = r'D:\codex\V18\test_run_judgment\程颖_答辩状_锋芒毕露.md'
write_md(defense_sharp, md_sharp, '民事答辩状(锋芒毕露版)')
if defense_sharp:
    pdf = render_to_pdf(defense_sharp, '民事答辩状', '07_答辩状_锋芒毕露')
    if pdf:
        desktop = shutil.copy(pdf, r'C:\Users\哆哆\Desktop\程颖_答辩状_锋芒毕露.pdf')
        print(f"✅ 锋芒版 PDF: {pdf}")
        print(f"   桌面: {desktop}")

# 答辩状 笑面虎
md_tiger = r'D:\codex\V18\test_run_judgment\程颖_答辩状_笑面虎.md'
write_md(defense_tiger, md_tiger, '民事答辩状(笑面虎版)')
if defense_tiger:
    pdf = render_to_pdf(defense_tiger, '民事答辩状', '07_答辩状_笑面虎')
    if pdf:
        desktop = shutil.copy(pdf, r'C:\Users\哆哆\Desktop\程颖_答辩状_笑面虎.pdf')
        print(f"✅ 笑面虎版 PDF: {pdf}")
        print(f"   桌面: {desktop}")

# ── 7. 反诉状(模板填充,绕开 LLM) ────────────────────────────────────────

counter_claim = build_counter_claim_text(
    fc=fc,
    identity='被诉方（被告）',
    counter_claim_type='超标的保全',
    user_info=user_info,
    request_items=[
        "1. 请求法院依法确认被反诉人申请财产保全的金额(56,804元)明显超出本案实际争议金额,构成超标的保全;",
        "2. 请求法院判令被反诉人赔偿反诉人因超额保全所遭受的损失(具体数额待反诉人举证后确定);",
        "3. 请求法院判令被反诉人承担反诉人因超额保全所额外承担的保全费用;",
        "4. 本案反诉费用由被反诉人承担。",
    ],
)

md_counter = r'D:\codex\V18\test_run_judgment\程颖_反诉状_超标的保全.md'
write_md(counter_claim, md_counter, '民事反诉状(超标的保全)')
pdf = render_to_pdf(counter_claim, '民事反诉状', '08_反诉状_超标的保全')
if pdf:
    desktop = shutil.copy(pdf, r'C:\Users\哆哆\Desktop\程颖_反诉状_超标的保全.pdf')
    print(f"✅ 反诉状 PDF: {pdf}")
    print(f"   桌面: {desktop}")

# ── 8. 杀伤力指数评估 ──────────────────────────────────────────────────

print()
print("=" * 70)
print("杀伤力指数评估")
print("=" * 70)
for label, content in [("锋芒答辩状", defense_sharp),
                       ("笑面虎答辩状", defense_tiger),
                       ("反诉状", counter_claim)]:
    score = compute_lethality_score(content)
    print(f"  {label}: {score}/100")
