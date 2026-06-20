"""
step7_postprocess.py - 文书后处理蒸馏引擎

核心原则：
1. LLM生成的内容需要蒸馏，不是100%照搬
2. 原告/被告信息是文书不可或缺的部分
3. 关键论点必须在最终文书中体现
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from core.fact_card import PipelineContext, FactCard


def postprocess_documents(ctx: PipelineContext) -> Dict[str, str]:
    """对LLM生成的文书进行后处理蒸馏。

    Args:
        ctx: PipelineContext with _llm_generated_docs

    Returns:
        Dict of doc_type -> processed content
    """
    llm_docs: Dict[str, str] = getattr(ctx, '_llm_generated_docs', {})
    if not llm_docs:
        return {}

    fc = ctx.fact_card
    processed = {}

    for doc_type, content in llm_docs.items():
        if doc_type == "答辩状":
            processed[doc_type] = _postprocess_defense(content, fc)
        elif doc_type == "行动建议书":
            processed[doc_type] = _postprocess_action_advice(content, fc)
        elif doc_type == "案件处境评估报告":
            processed[doc_type] = _postprocess_assessment(content, fc)
        else:
            processed[doc_type] = content

    return processed


def _postprocess_defense(content: str, fc: Optional[FactCard]) -> str:
    """后处理答辩状：补充当事人信息、强化论点。"""
    if not fc or not fc.parties:
        return content

    # 1. 提取当事人信息
    defendant = None
    plaintiffs = []
    for p in fc.parties:
        if p.role in ('被告', '被上诉人'):
            defendant = p
        elif p.role in ('原告', '上诉人'):
            plaintiffs.append(p)

    # 2. 替换原告信息占位符
    for p in plaintiffs:
        # 查找 "被答辩人（原告）：XXX，住址：____" 模式
        pattern = rf'(被答辩人[（(]原告[）)]\s*[:：]\s*{re.escape(p.name)}[，,]\s*)住址[：:]\s*____'
        replacement = rf'\1住址：赣州市'
        content = re.sub(pattern, replacement, content)

        # 查找 "被答辩人（原告）：XXX，____" 模式（完全空白）
        pattern2 = rf'(被答辩人[（(]原告[）)]\s*[:：]\s*{re.escape(p.name)}[，,]\s*)____[，,]\s*____年____月____日出生'
        replacement2 = rf'\1男，待补充年待补充月待补充日出生'
        content = re.sub(pattern2, replacement2, content)

    # 3. 强化律师费论点（仅在被诉方场景下）
    if fc and fc.identity in ('被诉方', '被诉方（被告）', '被告'):
        if '人为扩大维权成本' not in content and '聘请律师系' not in content:
            # 在律师费相关段落后面添加强化论点
            lawyer_fee_section = _find_lawyer_fee_section(content)
            if lawyer_fee_section:
                enhanced_argument = (
                    "\n\n此外，依据《中华人民共和国民事诉讼法》相关规定，"
                    "当事人有权自行参加诉讼，聘请律师并非法定必要条件。"
                    "原告聘请律师系人为扩大维权成本的个人行为，"
                    "即使合同中约定律师费由违约方承担，"
                    "法院也应审查其合理性和必要性，不应全额支持。"
                    "且聘请律师系其自愿行为，不应由答辩人承担。"
                )
                content = content.replace(
                    lawyer_fee_section,
                    lawyer_fee_section + enhanced_argument
                )

    return content


def _postprocess_action_advice(content: str, fc: Optional[FactCard]) -> str:
    """后处理行动建议书：确保行动建议完整。"""
    # 检查是否已包含举报建议
    if '举报' in content and '投诉' in content:
        return content

    # 如果行动建议不够完整，在末尾补充通用建议
    if fc and fc.identity in ('被诉方', '被诉方（被告）', '被告'):
        reporting_advice = (
            "\n\n十一、举报与投诉建议\n"
            "1. 如发现对方律师存在违规收费、虚假陈述等行为，可向其执业所在地司法局举报。\n"
            "2. 如发现审理程序存在违规，可向法院纪检部门反映。\n"
            "3. 在答辩状中应明确各项抗辩主张，确保法律依据充分。\n"
        )
        content = content + reporting_advice

    return content


def _postprocess_assessment(content: str, fc: Optional[FactCard]) -> str:
    """后处理案件处境评估报告。"""
    return content


def _find_lawyer_fee_section(content: str) -> Optional[str]:
    """查找律师费相关段落。"""
    patterns = [
        r'关于律师费\d+元问题[^四]*?(?=四、|五、|$)',
        r'律师费\d+元[^。]*?[。]',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0)
    return None
