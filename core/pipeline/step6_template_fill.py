"""
step6_template_fill.py - Pipeline Step 6: Template Loading & Filling

Loads scenario-specific YAML templates based on the user's identity and goal,
then fills template slots with data from the DistilledCard. Produces
document content strings ready for rendering in Step 7.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import yaml

from core.fact_card import PipelineContext, DistilledCard
from core.scenario_router import get_expected_doc_types


def _load_template(template_path: str) -> Dict[str, Any]:
    """Load a YAML template file and return its contents.

    Args:
        template_path: Absolute path to the YAML template file.

    Returns:
        Parsed template dictionary.

    Raises:
        FileNotFoundError: If template file does not exist.
        yaml.YAMLError: If template file is malformed.
    """
    with open(template_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fill_template_section(
    section: Dict[str, Any],
    distilled: DistilledCard,
    identity: str,
    goal: str,
) -> str:
    """Fill a single template section with distilled card data.

    Template sections contain placeholder tokens like:
      {{fact_card.case_id}}, {{fact_card.parties}}, {{strategy_card.situation_assessment}},
      {{identity}}, {{goal}}, etc.

    Args:
        section: Template section dict with 'title' (or 'heading') and 'content' keys.
        distilled: The DistilledCard containing all extracted data.
        identity: User identity string.
        goal: User goal string.

    Returns:
        Filled content string with placeholders replaced by actual data.
    """
    # Support both 'title' and 'heading' keys
    title = section.get("title", "") or section.get("heading", "")
    content_template = section.get("content", "")

    fc = distilled.fact_card
    sc = distilled.strategy_card

    # Extract party names
    defendant_name = ""
    plaintiff_name = ""
    if fc and fc.parties:
        for p in fc.parties:
            if "被告" in (p.role or ""):
                defendant_name = p.name or "答辩人"
            elif "原告" in (p.role or ""):
                plaintiff_name = p.name or "被答辩人"

    # Build case-specific opinions from key_facts and strategy
    key_facts_text = _format_list(fc.key_facts) if fc and fc.key_facts else "根据案件材料，双方之间存在借款关系。"
    delivery_opinion = "无异议" if fc and fc.key_facts else "有异议，需进一步核实"
    deadline_opinion = f"根据借款协议，借款期限为{fc.deadline}。" if fc and fc.deadline else "借款期限以借款协议约定为准。"
    interest_opinion = f"被答辩人主张按年利率6%计算利息。答辩人认为应以实际借款金额和借款期限为基数计算。" if fc and fc.amount else "利息计算方式需根据借款协议和实际借款金额确定。"
    collection_opinion = "被答辩人主张多次催要，答辩人对催收事实和时间有异议，需提供催收记录证明。"
    evidence_opinion = "答辩人对被答辩人提交的证据的真实性、关联性、合法性提出质证意见，具体详见答辩意见。"
    mediation_opinion = "答辩人愿意在查明案件事实的基础上，与被答辩人协商解决纠纷。"

    from datetime import datetime
    current_date = datetime.now().strftime("%Y年%m月%d日")

    # Build replacement map
    replacements = {
        "{{identity}}": identity,
        "{{goal}}": goal,
        "{{case_id}}": fc.case_id or "案件编号待确认",
        "{{court}}": fc.court or "管辖法院待确认",
        "{{amount}}": fc.amount or "争议金额待确认",
        "{{deadline}}": fc.deadline or "关键期限待确认",
        "{{situation_assessment}}": sc.situation_assessment or "案件评估正在进行中",
        "{{sabcd_rating}}": sc.sabcd_rating or "评级生成中",
        "{{parties}}": _format_parties(fc),
        "{{key_facts}}": key_facts_text,
        "{{disputed_facts}}": _format_list(fc.disputed_facts),
        "{{missing_materials}}": _format_list(fc.missing_materials),
        "{{conflicts}}": _format_list(fc.conflicts),
        "{{source_refs}}": _format_sources(fc),
        "{{action_advice}}": _format_action_advice(sc),
        "{{evidence_gap}}": _format_list(sc.evidence_gap),
        "{{risk_warnings}}": _format_list(sc.risk_warnings),
        "{{draft_documents}}": _format_draft_documents(sc),
        # New defense-specific variables
        "{{defendant_name}}": defendant_name,
        "{{plaintiff_name}}": plaintiff_name,
        "{{case_type}}": "借款合同纠纷" if "借款" in (fc.court or "") else "民间借贷纠纷",
        "{{delivery_opinion}}": delivery_opinion,
        "{{deadline_opinion}}": deadline_opinion,
        "{{interest_opinion}}": interest_opinion,
        "{{collection_opinion}}": collection_opinion,
        "{{evidence_opinion}}": evidence_opinion,
        "{{mediation_opinion}}": mediation_opinion,
        "{{current_date}}": current_date,
    }

    # Apply replacements
    filled_title = title
    filled_content = content_template
    for placeholder, value in replacements.items():
        filled_title = filled_title.replace(placeholder, value)
        filled_content = filled_content.replace(placeholder, value)

    return f"{filled_title}\n\n{filled_content}"


def _format_parties(fc) -> str:
    """Format parties list into readable string."""
    if not fc or not fc.parties:
        return ""
    lines = []
    for p in fc.parties:
        role_label = p.role or "未知角色"
        name_label = p.name or "未知"
        lines.append(f"  {role_label}: {name_label}")
    return "\n".join(lines)


def _format_list(items: List[str]) -> str:
    """Format a list of strings into numbered items, stripping distiller tags."""
    if not items:
        return ""
    import re
    cleaned = []
    for item in items:
        # Strip distiller tags
        clean = item.replace("【待核对】", "").replace("【争议】", "").replace("【待补充】", "").replace("【冲突】", "").strip()
        if clean:
            cleaned.append(clean)
    if not cleaned:
        return ""
    return "\n".join(f"  {i}. {item}" for i, item in enumerate(cleaned, 1))


def _format_sources(fc) -> str:
    """Format source references into readable string."""
    if not fc or not fc.source_refs:
        return ""
    lines = []
    for i, ref in enumerate(fc.source_refs, 1):
        page_info = f"（第{ref.page}页）" if ref.page else ""
        lines.append(f"  {i}. {ref.file_name}{page_info}: {ref.excerpt[:80]}")
    return "\n".join(lines)


def _format_action_advice(sc) -> str:
    """Format action advice into readable string."""
    if not sc or not sc.action_advice:
        return ""
    lines = []
    for i, advice in enumerate(sc.action_advice, 1):
        priority_label = advice.priority or "无"
        lines.append(f"  {i}. [{priority_label}] {advice.action}")
        if advice.reasoning:
            lines.append(f"     理由: {advice.reasoning}")
    return "\n".join(lines)


def _format_draft_documents(sc) -> str:
    """Format draft documents into readable string."""
    if not sc or not sc.draft_documents:
        return ""
    lines = []
    for i, doc in enumerate(sc.draft_documents, 1):
        lines.append(f"  {i}. 【{doc.doc_type}】{doc.title}")
        if doc.content:
            preview = doc.content[:200]
            if len(doc.content) > 200:
                preview += "..."
            lines.append(f"     {preview}")
    return "\n".join(lines)


def _get_template_filename(doc_type: str) -> str:
    """Map document type to template filename.

    Args:
        doc_type: Document type name (e.g., '答辩状')

    Returns:
        Template filename without extension (e.g., 'defense_template')
    """
    mapping = {
        "投诉状": "complaint_template",
        "起诉状": "lawsuit_template",
        "答辩状": "defense_template",
        "行政复议申请书": "administrative_review_template",
        "证据目录": "evidence_catalog",
        "案件处境评估报告": "common_case_assessment",
        "行动建议书": "action_advice",
        "证据闭环补强清单": "evidence整理_template",
    }
    return mapping.get(doc_type, doc_type)


def step6_template_fill(ctx: PipelineContext) -> PipelineContext:
    """Load YAML templates and fill them with distilled card data.

    Actions:
    1. Determine expected document types via scenario_router
    2. Load corresponding YAML templates from templates/ directory
    3. Fill each template with distilled_card data
    4. Create ctx.output_dir/customer/ directory
    5. Store filled content in ctx._filled_templates for Step 7

    Args:
        ctx: PipelineContext with distilled_card populated from Step 5.

    Returns:
        PipelineContext with _filled_templates attribute containing
        filled document content strings.
    """
    ctx.log("Step 6: 模板填充 - 加载场景模板并填充蒸馏数据")

    if ctx.distilled_card is None:
        ctx.add_error("distilled_card 为空，无法执行模板填充")
        return ctx

    # Determine expected document types for this identity/goal
    try:
        expected_docs = get_expected_doc_types(ctx.identity)
    except Exception as exc:
        ctx.log(f"WARNING: 场景路由失败，使用默认文档列表: {exc}")
        expected_docs = _get_default_doc_types(ctx.identity)

    ctx.log(f"  预期文档类型: {', '.join(expected_docs)}")

    # Create output/customer/ directory
    customer_dir = os.path.join(ctx.output_dir, "customer")
    try:
        os.makedirs(customer_dir, exist_ok=True)
        ctx.log(f"  输出目录已创建: {customer_dir}")
    except OSError as exc:
        ctx.add_error(f"无法创建输出目录 {customer_dir}: {exc}")
        return ctx

    # Load and fill templates
    filled_templates: Dict[str, str] = {}
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")

    for doc_type in expected_docs:
        template_name = _get_template_filename(doc_type)
        template_path = os.path.join(templates_dir, f"{template_name}.yaml")

        if os.path.exists(template_path):
            try:
                template = _load_template(template_path)
                sections = template.get("sections", [])

                filled_parts = []
                for section in sections:
                    filled_text = _fill_template_section(
                        section, ctx.distilled_card, ctx.identity, ctx.goal
                    )
                    filled_parts.append(filled_text)

                filled_content = "\n\n".join(filled_parts)
                filled_templates[doc_type] = filled_content
                ctx.log(f"  模板填充成功: {doc_type} ({len(filled_content)} 字符)")

            except yaml.YAMLError as exc:
                ctx.log(f"WARNING: 模板 {template_name}.yaml 解析失败: {exc}")
                filled_templates[doc_type] = _generate_fallback_content(
                    doc_type, ctx
                )
            except Exception as exc:
                ctx.log(f"WARNING: 模板 {template_name}.yaml 填充失败: {exc}")
                filled_templates[doc_type] = _generate_fallback_content(
                    doc_type, ctx
                )
        else:
            ctx.log(f"  模板文件不存在: {template_path}，生成备选内容")
            filled_templates[doc_type] = _generate_fallback_content(doc_type, ctx)

    # Store filled templates on context for Step 7 to use
    ctx._filled_templates = filled_templates  # type: ignore[attr-defined]
    ctx._customer_dir = customer_dir  # type: ignore[attr-defined]

    ctx.log(
        f"Step 6 完成: 填充了 {len(filled_templates)} 个模板"
    )

    return ctx


def _get_default_doc_types(identity: str) -> List[str]:
    """Provide default document types when scenario_router is unavailable.

    Args:
        identity: User identity string.

    Returns:
        List of default document type identifiers.
    """
    defaults = {
        "投诉方": ["投诉状", "证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
        "起诉方": ["起诉状", "证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
        "被诉方（被告）": ["答辩状", "证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
        "行政复议申请人": ["行政复议申请书", "证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
        "整理证据": ["证据目录", "案件处境评估报告", "行动建议书", "证据闭环补强清单"],
    }
    return defaults.get(identity, ["证据目录", "案件处境评估报告", "行动建议书"])


def _generate_fallback_content(doc_type: str, ctx: PipelineContext) -> str:
    """Generate minimal fallback content when template is missing.

    Args:
        doc_type: The document type identifier.
        ctx: PipelineContext for context data.

    Returns:
        A minimal content string with placeholder information.
    """
    fc = ctx.distilled_card.fact_card if ctx.distilled_card else None
    sc = ctx.distilled_card.strategy_card if ctx.distilled_card else None

    case_info = f"案件编号: {fc.case_id}" if fc and fc.case_id else "案件编号: 待确定"
    court_info = f"受理法院: {fc.court}" if fc and fc.court else ""

    header = f"{doc_type}\n\n{case_info}\n{court_info}\n\n"

    if doc_type == "案件处境评估报告" and sc:
        return header + (sc.situation_assessment or "案件评估正在进行中，请稍后查看完整报告。")
    elif doc_type == "行动建议书" and sc:
        if sc.action_advice:
            advice_text = "\n\n".join(
                f"【{a.priority}级建议】{a.action}\n理由: {a.reasoning}"
                for a in sc.action_advice
            )
            return header + advice_text
        return header + "行动建议正在生成中，请稍后查看完整报告。"
    elif doc_type == "证据闭环补强清单" and sc:
        if sc.evidence_gap:
            gaps_text = "\n".join(f"{i}. {g}" for i, g in enumerate(sc.evidence_gap, 1))
            return header + gaps_text
        return header + "证据补强清单正在生成中，请稍后查看完整报告。"
    elif doc_type == "证据目录":
        return header + _format_sources(fc) if fc else header + "证据目录正在生成中，请稍后查看完整报告。"
    else:
        return header + f"【{doc_type}】内容由系统生成，需专业律师审核完善。"
