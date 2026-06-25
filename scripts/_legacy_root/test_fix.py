"""测试修复是否有效"""
import sys
sys.path.insert(0, '.')

from core.fact_card import FactCard, Party
from core.providers.api_b_client import ApiBClient

# 创建一个简单的FactCard
fact_card = FactCard(
    case_id="测试案件",
    court="测试法院",
    parties=[
        Party(name="原告", role="原告"),
        Party(name="被告", role="被告"),
    ],
    identity="被诉方（被告）",
)

# 创建ApiBClient
client = ApiBClient()

# 测试_build_draft_documents
drafts = client._build_draft_documents(fact_card, "被诉方（被告）", "应诉答辩")
print(f"生成的文书草稿数量: {len(drafts)}")
for draft in drafts:
    print(f"  - {draft.doc_type}: {draft.title}")
    print(f"    内容长度: {len(draft.content)} 字符")

# 测试_build_actions
actions = client._build_actions(fact_card, "被诉方（被告）")
print(f"\n生成的行动建议数量: {len(actions)}")
for i, action in enumerate(actions[:3], 1):
    print(f"  {i}. [{action.priority}] {action.action[:50]}...")