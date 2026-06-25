"""debug_extract.py — 验证 _extract_user_info_from_refs"""
import sys
sys.path.insert(0, '.')
sys.dont_write_bytecode = True
import json
from core.fact_card import FactCard, Party, SourceRef
from core.pipeline.step7_render import _extract_user_info_from_refs

with open(r'D:\codex\V18\test_run_judgment\output_程颖\_internal\distilled_card.json', 'r', encoding='utf-8') as f:
    distilled_data = json.load(f)

fc_data = distilled_data['fact_card']
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
    source_refs=source_refs,
)

# 测试 1:ctx=None(我之前用的方式)
print("=== ctx=None ===")
ui_none = _extract_user_info_from_refs(fc, None)
print(f"抽到的姓名: {list(ui_none.keys())}")
for n, info in ui_none.items():
    print(f"  {n}: {info}")

# 测试 2:ctx 带 raw_texts(标准方式)
print()
print("=== ctx=有 raw_texts ===")
class FakeCtx:
    def __init__(self, raw_texts):
        self.raw_texts = raw_texts
# 把 source_refs 的 excerpt 模拟为 raw_texts
raw_texts = [s.excerpt for s in source_refs if s.excerpt]
ctx = FakeCtx(raw_texts)
ui_ctx = _extract_user_info_from_refs(fc, ctx)
print(f"抽到的姓名: {list(ui_ctx.keys())}")
for n, info in ui_ctx.items():
    print(f"  {n}: {info}")

# 测试 3:直接调 text_utils.extract_personal_info 验证原文可识别
print()
print("=== 直接测 extract_personal_info ===")
from core.text_utils import extract_personal_info
sample = "申请人:程颖颖,女,汉族,1981年8月22日出生,住安徽省六安市金安区开发区新加坡御苑14号楼1单元601室,身份证号:34240119810822102X,电话:17856432688"
info = extract_personal_info(sample)
print(f"  {info}")
