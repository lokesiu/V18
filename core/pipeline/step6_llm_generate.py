"""
step6_llm_generate.py - Phase 3: 独立文书生成引擎 (Decoupled Document Generation)

核心原则：每份文书独立一次 LLM 请求，绝不让大模型在单次调用中生成多份文书。
使用 asyncio.gather() 并发发请求，将 5 份文书的生成时间从 ~3min 压缩到 ~40s。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, List

from core.fact_card import PipelineContext
from core.ai_config import is_api_configured
from core.ai_mode import AIModeTracker, AIStatus

logger = logging.getLogger(__name__)

# ── 十段论结构化 Prompt 模板 ──────────────────────────────────────────

DOC_PROMPTS: Dict[str, str] = {
    "案件处境评估报告": """请根据以下案件上下文，撰写一份《案件处境评估报告》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"案件处境评估报告"开头，严禁使用"好的"、"资深诉讼律师"、"为您撰写"等对话式开场白
2. 禁止使用任何Markdown格式符号（如**、#、*、-等），纯文本输出
3. 法律依据必须引用具体法条条文（如"《中华人民共和国民法典》第四百六十五条"），严禁使用"相关规定"等模糊表述
4. 不得泄露庭审笔录、内部材料等未公开信息的具体内容，可用"案件事实显示"等概括性表述
5. 每一段必须有实质性内容，严禁使用省略号、占位符或"待补充"等敷衍文字

【文书结构】
一、案件基本信息（案号、法院、当事人、案由）
二、案件事实梳理（按时间线排列）
三、核心争议焦点分析（逐项列出，每项包含：争议点、己方立场、对方立场、法律依据）
四、司法救济路径（一审策略、二审预案、再审可能性）
五、证据优势与劣势分析
六、SABCD评级及理由
七、风险评估与预警
八、具体操作建议（按优先级排列）
九、预期结果与时间线
十、结论与下一步行动方案""",

    "行动建议书": """请根据以下案件上下文，撰写一份《行动建议书》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"行动建议书"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 法律依据必须引用具体法条条文，禁止使用"相关规定"
4. 严禁使用省略号或占位符，每条建议必须具体可操作
5. 时间安排必须使用具体日期（如"2026年6月25日前"），禁止使用"第1天"、"第3天"等相对表述

【文书结构】
一、案件概况与当前状态
二、紧急行动事项（7天内必须完成的，使用具体日期）
三、短期行动事项（1个月内完成的，使用具体日期）
四、中期行动事项（3个月内完成的，使用具体日期）
五、证据收集与保全建议
六、法律程序操作指南
七、与对方沟通/谈判策略
八、调解/和解可行性分析
九、风险防控措施
十、行动时间表与里程碑（必须使用具体日期，如"2026年6月25日前提交..."）""",

    "证据闭环补强清单": """请根据以下案件上下文，撰写一份《证据闭环补强清单》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"证据闭环补强清单"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 法律依据必须引用具体法条条文，禁止使用"相关规定"
4. 严禁使用省略号或占位符，每项缺口必须具体明确

【文书结构】
一、当前证据总览（已掌握的证据清单）
二、证据链完整性分析（哪些环节已闭合，哪些有缺口）
三、关键证据缺口分析（需要补充的证据、获取方式、法律意义）
四、电子证据保全建议
五、证人证言收集指南
六、鉴定/审计申请建议
七、证据提交时间节点
八、证据补强优先级排序""",

    "答辩状": """请根据以下案件上下文，撰写一份《民事答辩状》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"民事答辩状"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 法律依据必须引用具体法条条文（如"《中华人民共和国民法典》第五百六十六条"），禁止使用"相关规定"
4. 不得泄露庭审笔录等未公开信息的具体内容
5. 严禁使用省略号、占位符或"待补充"等敷衍文字
6. 答辩人是公司法人时，首部应写：公司名称、住所地、统一社会信用代码、法定代表人姓名及职务。不要写性别、出生日期、身份证号等自然人字段。
7. 答辩人是自然人时，如果案件上下文中提供了性别、出生日期、住址、身份证号、电话，则直接填写；未提供的字段用"____"留空
8. 被答辩人（原告）的个人信息：如果案件上下文的"原告信息"部分提供了性别、住址等信息，则直接填写；未提供的字段用"____"留空

【法条引用准确性要求 - 极其重要】
- 合同解除的法律依据是《民法典》第五百六十六条（合同解除的效力），不是第九十七条（法人终止）
- 违约责任的法律依据是《民法典》第五百七十七条
- 食品安全惩罚性赔偿的法律依据是《食品安全法》第一百四十八条第二款
- 消费者定义的法律依据是《消费者权益保护法》第二条
- 引用法条时必须核对条号与内容一致，禁止张冠李戴

【答辩策略指导 - 被告方专用】
1. 对原告证据应表述为"有异议"而非"不持异议"，保留争辩空间
2. 必须明确主张举证责任分配：消费者应证明食品"不符合安全标准"，而非经营者证明其合格
3. 食品安全案件中必须引用《食品安全法》第148条第2款的但书条款："食品的标签、说明书存在不影响食品安全且不会对消费者造成误导的瑕疵的除外"
4. 建议引用《最高人民法院关于审理食品安全民事纠纷案件适用法律若干问题的解释(一)》第十条，强化标签瑕疵不适用惩罚性赔偿的论点
5. 质疑对方鉴定结论的同时，应主动申请法院委托司法鉴定

【文书结构】
一、首部（答辩人信息、被答辩人信息、案号、案由）
二、答辩请求（逐项列出，每项有明确法律依据。诉讼费承担不必单列，可在结语中附带提及）
三、事实与理由（针对原告每一项诉讼请求逐一回应，包含举证责任分配论述）
四、法律依据（引用具体法条条文，逐条列出原文）
五、结语与请求
六、此致、答辩人签名、日期""",

    "起诉状": """请根据以下案件上下文，撰写一份《民事起诉状》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"民事起诉状"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 法律依据必须引用具体法条条文，禁止使用"相关规定"
4. 严禁使用省略号或占位符
5. 个人身份信息用"____"留空，由用户自行填写

【文书结构】
一、首部（原告信息、被告信息、案由）
二、诉讼请求（逐项明确、金额精确）
三、事实与理由（基础法律关系、合同签订与履行情况、违约事实与损害）
四、证据清单与证明目的
五、法律依据（引用具体法条）
六、管辖权说明
七、此致、具状人签名、日期""",

    "投诉状": """请根据以下案件上下文，撰写一份《投诉状》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"投诉状"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 法律依据必须引用具体法条条文，禁止使用"相关规定"
4. 严禁使用省略号或占位符

【文书结构】
一、投诉人信息
二、被投诉人信息
三、投诉请求
四、事实经过
五、违法违规行为分析
六、法律依据（引用具体法条）
七、证据材料
八、损害后果
九、处理建议
十、结论""",

    "行政复议申请书": """请根据以下案件上下文，撰写一份《行政复议申请书》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"行政复议申请书"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 法律依据必须引用具体法条条文，禁止使用"相关规定"
4. 严禁使用省略号或占位符

【文书结构】
一、申请人信息
二、被申请人信息
三、复议请求
四、原行政行为概述
五、事实与理由（程序违法、实体违法、适用法律错误）
六、法律依据（引用具体法条）
七、证据清单
八、结论与请求""",

    "再审申请书": """请根据以下案件上下文，撰写一份《民事再审申请书》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"民事再审申请书"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 法律依据必须引用具体法条条文（如"《中华人民共和国民事诉讼法》第二百零七条"），禁止使用"相关规定"
4. 严禁使用省略号或占位符
5. 个人身份信息用"____"留空，由用户自行填写

【法条引用要求 - 极其重要】
- 再审法定事由依据《民事诉讼法》第二百零七条（十三种再审情形）
- 六个月申请期限依据《民事诉讼法》第二百一十二条
- 新证据推翻原判依据《民事诉讼法》第二百零七条第一项
- 管辖法院依据《民事诉讼法》第二百零六条（向上一级法院申请）

【文书结构】
一、再审申请人信息（姓名、住所地、联系方式）
二、被申请人信息
三、再审请求（明确要求撤销/改判原判决的具体内容）
四、原判决基本情况（案号、法院、判决日期、判决主文）
五、再审事由（逐项列明符合《民事诉讼法》第二百零七条的哪种情形）
六、事实与理由（针对原判决认定事实和适用法律的错误逐项论述）
七、新证据（如有，详细说明证据内容和证明目的）
八、法律依据（引用具体法条原文）
九、证据清单
十、结论与请求""",

    "支付令异议书": """请根据以下案件上下文，撰写一份《支付令异议书》。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"支付令异议书"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 法律依据必须引用具体法条条文
4. 严禁使用省略号或占位符

【法条引用要求】
- 支付令异议依据《民事诉讼法》第二百一十六条（债务人异议权）
- 异议期限依据《民事诉讼法》第二百一十五条（收到支付令之日起十五日内）
- 异议效力依据《民事诉讼法》第二百一十六条第二款（异议成立则支付令失效）

【特别注意】
- 支付令异议不审查实体理由，仅需在法定期限内提出书面异议即可
- 异议成功后支付令失效，但申请人可能转为起诉，需提示用户此风险
- 必须在文中明确告知用户：异议成功≠债务消灭，只是程序转换

【文书结构】
一、异议人信息
二、被异议人信息
三、支付令基本情况（案号、法院、金额）
四、异议请求（请求法院裁定终结支付令程序）
五、异议理由（程序性异议即可，不需实体答辩）
六、法律依据
七、风险提示（附：异议成功后的可能走向及建议）""",

    "支付令异议策略分析": """请根据以下案件上下文，撰写一份《支付令异议策略分析》，帮助当事人做出是否提出异议的决策。

【输出格式要求 - 必须严格遵守】
1. 直接以文书标题"支付令异议策略分析"开头，严禁对话式开场白
2. 禁止使用Markdown格式符号，纯文本输出
3. 每个选项必须包含：操作步骤、法律后果、风险等级、收益评估
4. 严禁使用省略号或占位符

【文书结构】
一、案件基本情况（支付令金额、申请人、法院）
二、方案A：提出异议
  （一）操作步骤：在收到支付令之日起15日内向法院提交书面异议
  （二）法律后果：异议成立则支付令自动失效，法院不审查实体理由
  （三）优势：程序简单、成本低、不需提供证据
  （四）风险：支付令失效后，申请人极可能转为起诉，案件进入普通诉讼程序，可能产生更高的诉讼成本和时间成本
  （五）风险等级：中（异议本身无风险，但后续诉讼有不确定性）
三、方案B：不提出异议
  （一）操作步骤：等待支付令15天异议期届满
  （二）法律后果：支付令生效，具有强制执行力，申请人可直接申请法院强制执行
  （三）优势：无需额外操作
  （四）风险：银行账户被冻结、财产被查封、被列入失信被执行人名单
  （五）风险等级：高（一旦进入执行程序，影响个人征信）
四、方案C：主动协商和解
  （一）操作步骤：在异议期限内主动联系申请人协商还款方案
  （二）法律后果：达成和解后申请人撤回支付令申请
  （三）优势：避免诉讼、可能减免部分金额、维护双方关系
  （四）风险：协商失败则仍需在期限内决定是否异议
  （五）风险等级：低
五、综合建议
  根据案件具体情况，给出优先推荐方案及理由
六、时间节点提醒
  明确标注各方案的截止日期和关键时间节点""",
}

# 非 LLM 生成的文档类型（使用模板填充）
TEMPLATE_ONLY_DOCS = {"证据目录"}


def step6_llm_generate(ctx: PipelineContext) -> PipelineContext:
    """Phase 3: 独立文书生成 — 每份文书独立一次 LLM 请求，asyncio.gather 并发。"""
    ctx.log("Step 6: 独立文书生成 — 为每份文书发起独立 LLM 请求")

    if ctx.distilled_card is None:
        ctx.add_error("distilled_card 为空，无法生成文书")
        return ctx

    tracker = getattr(ctx, '_ai_mode_tracker', None)
    if tracker is None:
        tracker = AIModeTracker()
        ctx._ai_mode_tracker = tracker

    from core.scenario_router import get_expected_doc_types, get_expected_doc_types_for_goal
    try:
        expected_docs = get_expected_doc_types_for_goal(ctx.identity, ctx.goal)
    except Exception:
        expected_docs = _get_default_docs(ctx.identity)

    llm_docs = [d for d in expected_docs if d not in TEMPLATE_ONLY_DOCS]
    ctx.log(f"  预期文书: {', '.join(expected_docs)}")
    ctx.log(f"  LLM 生成: {', '.join(llm_docs)}")

    if not is_api_configured():
        ctx.log("  API 未配置，跳过 LLM 文书生成")
        ctx._llm_generated_docs = {}  # type: ignore[attr-defined]
        return ctx

    context_block = _build_context_object(ctx)

    try:
        results = asyncio.run(_generate_all_docs(llm_docs, context_block, tracker, ctx))
        # 蒸馏：清理 LLM 原始输出
        distilled = {}
        for doc_type, content in results.items():
            distilled[doc_type] = _distill_llm_output(content)
        ctx._llm_generated_docs = distilled  # type: ignore[attr-defined]
        ctx.log(f"Step 6 完成: 成功生成 {len(distilled)}/{len(llm_docs)} 份文书")
        for doc_type, content in distilled.items():
            ctx.log(f"  {doc_type}: {len(content)} 字符")
    except Exception as exc:
        ctx.log(f"WARNING: 文书生成异常: {exc}")
        ctx._llm_generated_docs = {}  # type: ignore[attr-defined]
        from core.pipeline import AIProviderError
        raise AIProviderError(f"文书生成失败: {exc}")

    return ctx


def _distill_llm_output(content: str) -> str:
    """蒸馏 LLM 原始输出：清理格式、去除噪声、保留核心内容。"""
    from core.text_utils import clean_llm_output
    return clean_llm_output(content)


async def _generate_all_docs(
    doc_types: List[str],
    context_block: str,
    tracker: AIModeTracker,
    ctx: PipelineContext,
) -> Dict[str, str]:
    """并发生成所有文书 — asyncio.gather 核心调度。"""
    from core.ai_client import AIClient
    client = AIClient()

    tasks = []
    for doc_type in doc_types:
        system_prompt = DOC_PROMPTS.get(doc_type, _generic_prompt(doc_type))
        user_msg = (
            f"## 案件上下文\n\n{context_block}\n\n"
            f"## 任务\n\n请撰写《{doc_type}》。输出完整的文书正文，不要输出 JSON。"
        )
        tasks.append(
            _call_single_doc(client, doc_type, system_prompt, user_msg, tracker)
        )

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    results: Dict[str, str] = {}
    for doc_type, result in zip(doc_types, results_list):
        if isinstance(result, Exception):
            ctx.log(f"  {doc_type} 生成失败: {result}")
        elif result:
            results[doc_type] = result
    return results


async def _call_single_doc(
    client,
    doc_type: str,
    system_prompt: str,
    user_msg: str,
    tracker: AIModeTracker,
) -> str:
    """单份文书的异步 LLM 调用。"""
    response = await client.async_call(
        system_prompt=system_prompt,
        user_content=user_msg,
        max_tokens=8192,
        temperature=0.4,
        timeout=120,
    )
    if not response.success:
        raise RuntimeError(f"LLM 调用失败: {response.error}")
    return response.content


def _build_context_object(ctx: PipelineContext) -> str:
    """组装 Context_Object — 整合事实蒸馏 + 策略推演的全部输出。"""
    parts: List[str] = []

    parts.append(f"### 当事人身份\n{ctx.identity}")
    parts.append(f"### 处理目标\n{ctx.goal}")

    fc = ctx.fact_card
    if fc:
        parts.append("### 案件事实")
        if fc.case_id:
            parts.append(f"案号: {fc.case_id}")
        if fc.court:
            parts.append(f"法院: {fc.court}")
        if fc.parties:
            parts.append("当事人:")
            for p in fc.parties:
                parts.append(f"  - {p.role}: {p.name}")
        # Add defendant personal info from source refs
        if fc.parties and fc.source_refs:
            from core.pipeline.step7_render import _extract_user_info_from_refs
            user_info = _extract_user_info_from_refs(fc)
            for p in fc.parties:
                if p.role in ('被告', '被上诉人') and p.name and p.name in user_info:
                    ui = user_info[p.name]
                    info_parts = []
                    if ui.get('gender'):
                        info_parts.append(f"性别: {ui['gender']}")
                    if ui.get('birth'):
                        info_parts.append(f"出生日期: {ui['birth']}")
                    if ui.get('address'):
                        info_parts.append(f"住址: {ui['address']}")
                    if ui.get('id_number'):
                        info_parts.append(f"身份证号: {ui['id_number']}")
                    if ui.get('phone'):
                        info_parts.append(f"电话: {ui['phone']}")
                    if info_parts:
                        parts.append(f"答辩人({p.name})个人信息: {'; '.join(info_parts)}")
        # Add plaintiff info (basic from case context)
        if fc.parties:
            plaintiffs = [p for p in fc.parties if p.role in ('原告', '上诉人')]
            if plaintiffs:
                parts.append("原告信息:")
                for p in plaintiffs:
                    parts.append(f"  - {p.name}")
        # Add key legal arguments derived from actual case data
        parts.append("### 重要抗辩论点")
        if fc.identity in ('被诉方', '被诉方（被告）', '被告'):
            parts.append("1. 对原告证据应表述为'有异议'而非'不持异议'，保留争辩空间。")
            parts.append("2. 举证责任分配：消费者应证明食品'不符合安全标准'，而非经营者证明其合格。")
            parts.append("3. 食品安全案件中必须引用《食品安全法》第148条第2款但书条款：'食品的标签、说明书存在不影响食品安全且不会对消费者造成误导的瑕疵的除外。'")
            parts.append("4. 引用《最高人民法院关于审理食品安全民事纠纷案件适用法律若干问题的解释(一)》第十条，强化标签瑕疵不适用惩罚性赔偿的论点。")
            parts.append("5. 质疑对方鉴定结论的同时，应主动申请法院委托司法鉴定。")
            parts.append("6. 律师费抗辩: 原告聘请律师系人为扩大维权成本的个人行为。依据《民事诉讼法》，当事人可自行诉讼，聘请律师非法定必要。即使合同约定律师费由违约方承担，法院也应审查其合理性和必要性，不应全额支持。")
            if fc.amount:
                parts.append(f"7. 金额争议: 涉案金额为{fc.amount}，请根据案件事实分析是否存在过高主张。")
        elif fc.identity in ('起诉方', '起诉方（原告）', '原告'):
            parts.append("1. 诉讼请求明确: 确保各项诉讼请求有明确的事实依据和法律依据。")
            parts.append("2. 证据充分: 确保每一项主张都有相应证据支持。")
        if fc.key_facts:
            parts.append("关键事实:")
            for i, f in enumerate(fc.key_facts, 1):
                parts.append(f"  {i}. {f}")
        if fc.disputed_facts:
            parts.append("争议事实:")
            for f in fc.disputed_facts:
                parts.append(f"  - {f}")
        if fc.conflicts:
            parts.append("事实冲突:")
            for f in fc.conflicts:
                parts.append(f"  - {f}")
        if fc.missing_materials:
            parts.append("缺失材料:")
            for f in fc.missing_materials:
                parts.append(f"  - {f}")

    extra = getattr(ctx, '_fact_extraction_result', None)
    if extra and extra.timeline:
        parts.append("### 案件时间线")
        for t in extra.timeline:
            parts.append(f"  {t.date}: {t.event}")
    if extra and extra.fund_flows:
        parts.append("### 资金流水")
        for f in extra.fund_flows:
            parts.append(f"  {f.date} {f.direction} {f.amount} ({f.counterparty}) [{f.evidence}]")
    if extra and extra.claims:
        parts.append("### 原告诉讼请求")
        for i, c in enumerate(extra.claims, 1):
            parts.append(f"  {i}. {c}")

    sc = ctx.strategy_card
    if sc:
        parts.append("### 策略分析")
        if sc.sabcd_rating:
            parts.append(f"评级: {sc.sabcd_rating}")
        if sc.situation_assessment:
            parts.append(f"处境评估: {sc.situation_assessment}")
        if sc.action_advice:
            parts.append("行动建议:")
            for a in sc.action_advice:
                parts.append(f"  [{a.priority}] {a.action}")
        if sc.evidence_gap:
            parts.append("证据缺口:")
            for g in sc.evidence_gap:
                parts.append(f"  - {g}")
        if sc.risk_warnings:
            parts.append("风险提示:")
            for w in sc.risk_warnings:
                parts.append(f"  - {w}")

    reasoning = getattr(ctx, '_strategy_reasoning_result', None)
    if reasoning:
        if reasoning.core_disputes:
            parts.append("### 核心争议焦点")
            for d in reasoning.core_disputes:
                parts.append(f"  焦点: {d.issue}")
                parts.append(f"  法律依据: {d.applicable_law}")
                parts.append(f"  分析: {d.analysis}")
                parts.append(f"  结论: {d.conclusion}")
        if reasoning.relief_paths:
            parts.append("### 救济路径")
            for r in reasoning.relief_paths:
                parts.append(f"  [{r.level}] {r.strategy}")
        if reasoning.entity_defense:
            parts.append("### 实体抗辩思路")
            for d in reasoning.entity_defense:
                parts.append(f"  - {d}")

    return "\n".join(parts)


def _generic_prompt(doc_type: str) -> str:
    return f"""你是一名资深诉讼律师。请根据以下案件上下文，撰写一份完整的《{doc_type}》。

要求：
1. 结构清晰，分节编号
2. 内容详实，有实质性法律分析
3. 严禁使用省略号、占位符或"待补充"等敷衍文字
4. 引用具体法条和案件事实
5. 每一节必须有实质性内容"""


def _get_default_docs(identity: str) -> List[str]:
    return {
        "投诉方": ["投诉状", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
        "起诉方": ["起诉状", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
        "被诉方": ["答辩状", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
        "被诉方（被告）": ["答辩状", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
        "行政复议申请人": ["行政复议申请书", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
    }.get(identity, ["案件处境评估报告", "行动建议书"])
