"""regenerate_retrial.py — 用修正版模板重新生成再审申请书"""
import sys
sys.path.insert(0, '.')
sys.dont_write_bytecode = True
import os

# 1. 加载真实案件的 distilled_card
import json
card_path = r"D:\codex\V18\test_run_judgment\output_v3\_internal\distilled_card.json"
with open(card_path, "r", encoding="utf-8") as f:
    distilled_card = json.load(f)

fc = distilled_card.get("fact_card", {})
sc = distilled_card.get("strategy_card", {})

# 2. 重建 FactCard / StrategyCard 对象(简化)
from core.fact_card import FactCard, Party, SourceRef, StrategyCard
from core.pipeline.step7_render import (
    _build_retrial_application_text,
    _extract_user_info_from_refs,
)

# 重建 parties
parties = []
for p_data in fc.get("parties", []):
    parties.append(Party(
        role=p_data.get("role", ""),
        name=p_data.get("name", ""),
    ))

# 重建 source_refs
source_refs = []
for s_data in fc.get("source_refs", []):
    source_refs.append(SourceRef(
        file_name=s_data.get("file_name", ""),
        excerpt=s_data.get("excerpt", ""),
        page=s_data.get("page", 0),
    ))

# 重建 FactCard
fact_card = FactCard(
    case_id=fc.get("case_id", ""),
    court=fc.get("court", ""),
    parties=parties,
    key_facts=fc.get("key_facts", []),
    disputed_facts=fc.get("disputed_facts", []),
    conflicts=fc.get("conflicts", []),
    missing_materials=fc.get("missing_materials", []),
    identity=fc.get("identity", "被诉方（被告）"),
    amount=fc.get("amount", ""),
    source_refs=source_refs,
)

# 重建 StrategyCard
strategy_card = StrategyCard(
    sabcd_rating=sc.get("sabcd_rating", ""),
    situation_assessment=sc.get("situation_assessment", ""),
    risk_warnings=sc.get("risk_warnings", []),
    action_advice=sc.get("action_advice", []),
    evidence_gap=sc.get("evidence_gap", []),
)

# 3. 抽取 user_info(从源文)
class FakeCtx:
    def __init__(self):
        self.fact_card = fact_card
        self.raw_texts = []

user_info = _extract_user_info_from_refs(fact_card, FakeCtx())

# 4. 调用模板生成修正版文书
text = _build_retrial_application_text(
    fc=fact_card,
    identity="被诉方（被告）",
    goal="申请再审",
    user_info=user_info,
    strategy_card=strategy_card,
)

print(f"生成文本长度: {len(text)} 字符")
print(f"含'风险与再审必要性'? {'风险与再审必要性' in text}")
print(f"含'((2026)'? {'((2026)' in text}")
print(f"含'((一)'? {'((一)' in text}")

# 5. 渲染为 DOCX
out_dir = r"D:\codex\V18\test_run_judgment\output_v3\customer"
os.makedirs(out_dir, exist_ok=True)
docx_path = os.path.join(out_dir, "06_再审申请书_江宁区全至惠百货超市店案.docx")

from core.render.docx_renderer import render_docx_from_text
render_docx_from_text(text, docx_path)
print(f"\nDOCX 已生成: {docx_path} ({os.path.getsize(docx_path)} bytes)")

# 6. 渲染为 PDF
pdf_path = docx_path.replace(".docx", ".pdf")
from core.render.pdf_converter import convert_to_pdf
ok = convert_to_pdf(docx_path, pdf_path)
print(f"PDF 生成: {ok} ({pdf_path}, {os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0} bytes)")

# 7. 复制到桌面方便用户查看
import shutil
desktop_pdf = r"C:\Users\哆哆\Desktop\再审申请书_v3_修正版.pdf"
shutil.copy2(pdf_path, desktop_pdf)
print(f"PDF 已复制到桌面: {desktop_pdf}")

# 8. 写入 markdown 方便阅读
md_path = r"D:\codex\V18\test_run_judgment\再审申请书_v3_修正版.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write("# 民事再审申请书(修正版 v3)\n\n")
    f.write(text)
print(f"Markdown 版: {md_path}")
