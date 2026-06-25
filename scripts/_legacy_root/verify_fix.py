"""验证所有修复是否正确生效"""
import os, sys, tempfile
sys.path.insert(0, '.')

from core.providers.api_b_client import ApiBClient
from core.fact_card import FactCard, Party
from core.scenario_router import get_sabcd_factors
from core.quality.final_artifact_auditor import _check_expected_files

# 1. api_b_client: 被诉方（被告）identity 生成文书草稿
client = ApiBClient()
fc1 = FactCard(case_id='test', parties=[Party(name='被告', role='被告')], identity='被诉方（被告）')
drafts1 = client._build_draft_documents(fc1, '被诉方（被告）', '应诉答辩')
print(f'[{ "OK" if len(drafts1)>0 else "FAIL" }] api_b_client 被诉方（被告）: {len(drafts1)} docs')

# 2. api_b_client: 起诉方 identity 生成文书草稿
fc2 = FactCard(case_id='test', parties=[Party(name='原告', role='原告')], identity='起诉方')
drafts2 = client._build_draft_documents(fc2, '起诉方', '起诉立案')
print(f'[{ "OK" if len(drafts2)>0 else "FAIL" }] api_b_client 起诉方: {len(drafts2)} docs')

# 3. scenario_router: 被诉方（被告）identity 匹配
factors = get_sabcd_factors('被诉方（被告）', '应诉答辩')
print(f'[{ "OK" if len(factors["criteria"])>0 else "FAIL" }] scenario_router: {len(factors["criteria"])} criteria')

# 4. distiller: 被诉方（被告）identity 匹配（多当事人场景）
from core.distiller import _fix_party_identity_confusion
fc3 = FactCard(case_id='test', parties=[
    Party(name='原告1', role='原告'),
    Party(name='原告2', role='原告'),
], identity='被诉方（被告）')

class FakeCtx:
    def log(self, s): print(f'  {s}')

_fix_party_identity_confusion(fc3, FakeCtx())
ok4 = fc3.parties[1].role == '被告'
print(f'[{ "OK" if ok4 else "FAIL" }] distiller: {fc3.parties[0].name}={fc3.parties[0].role}, {fc3.parties[1].name}={fc3.parties[1].role}')

# 5. final_artifact_auditor: 带后缀文件名匹配
with tempfile.TemporaryDirectory() as td:
    for name in ['01_案件处境评估报告_张三案.docx', '02_行动建议书_张三案.docx',
                 '03_证据闭环补强清单_张三案.docx', '05_可提交文书草稿_张三案.docx',
                 '06_答辩状_张三案.docx', 'test.pdf', 'test.zip']:
        open(os.path.join(td, name), 'w').close()
    result = _check_expected_files(td)
    print(f'[{ "OK" if result.passed else "FAIL" }] auditor 动态文件名: {result.message}')

# 6. 验证 step7_render.py extra_doc 返回中文 doc_type
from core.pipeline.step7_render import _get_identity_extra_doc
extra = _get_identity_extra_doc('被诉方（被告）')
ok6 = extra is not None and extra[1] == '答辩状'
print(f'[{ "OK" if ok6 else "FAIL" }] step7 extra_doc: {extra}')

# 总结
all_ok = (len(drafts1)>0 and len(drafts2)>0 and len(factors["criteria"])>0
          and ok4 and result.passed and ok6)
print(f'\n{"=== ALL 6 CHECKS PASSED ===" if all_ok else "=== SOME CHECKS FAILED ==="}')
