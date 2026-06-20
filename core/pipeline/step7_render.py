"""
step7_render.py - Pipeline Step 7: Document Rendering

Renders all documents from filled templates into DOCX, XLSX, and PDF
formats. Builds a customer delivery package (ZIP) containing all files.

This is the main document production step that creates the deliverables.
"""
from __future__ import annotations

import os
import zipfile
import traceback
from typing import Dict, List, Optional

from core.fact_card import PipelineContext
from core.render.docx_renderer import render_docx, render_docx_from_text
from core.render.xlsx_renderer import render_xlsx
from core.render.pdf_converter import convert_to_pdf
from core.render.zip_builder import build_zip


# Document ordering and naming for the delivery package
DOCUMENT_ORDER = [
    ("01_案件处境评估报告", "案件处境评估报告", "docx"),
    ("02_行动建议书", "行动建议书", "docx"),
    ("03_证据闭环补强清单", "证据闭环补强清单", "docx"),
    ("04_证据目录", "证据目录", "xlsx"),
    ("05_可提交文书草稿", "可提交文书草稿", "docx"),
]


def _get_identity_extra_doc(identity: str) -> Optional[tuple]:
    """Get the identity-specific extra document configuration.

    Args:
        identity: User identity string.

    Returns:
        Tuple of (file_prefix, doc_type, format) or None.
    """
    extras = {
        "投诉方": ("06_投诉状", "投诉状", "docx"),
        "起诉方": ("06_起诉状", "起诉状", "docx"),
        "被诉方": ("06_答辩状", "答辩状", "docx"),
        "被诉方（被告）": ("06_答辩状", "答辩状", "docx"),
        "行政复议申请人": ("06_行政复议申请书", "行政复议申请书", "docx"),
    }
    return extras.get(identity)


def _render_docx_from_content(
    content: str,
    output_path: str,
    ctx: PipelineContext,
) -> bool:
    """Render content to a DOCX file.

    Args:
        content: The document content string.
        output_path: Full path for the output DOCX file.
        ctx: PipelineContext for error logging.

    Returns:
        True if rendering succeeded, False otherwise.
    """
    try:
        # Post-process: Replace placeholder patterns from input materials
        import re
        # Replace [请填写...] bracket placeholder patterns (must be before ID/phone replacement)
        content = re.sub(r'\[请填写[^\]]*\]', '', content)
        content = re.sub(r'\[请补充[^\]]*\]', '', content)
        # Replace standalone XXX
        content = content.replace('XXX', '[已脱敏]')
        # Replace "类型:" patterns
        content = content.replace('类型:', '分类:')
        content = content.replace('类型：', '分类：')
        # Replace bare placeholder sentences (all variants)
        content = re.sub(r'请填写[^\n，。；]*', '', content)
        content = re.sub(r'请补充[^\n，。；]*', '', content)
        # Remove Markdown bold markers **text** -> text
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        # Remove Markdown heading markers ### text -> text
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        # Remove Markdown list markers at line start
        content = re.sub(r'^\s*[-*]\s+', '', content, flags=re.MULTILINE)
        # Remove LLM conversational opening patterns
        content = re.sub(r'^好的[，,。.!！\s]*', '', content)
        content = re.sub(r'资深诉讼律师[^。！\n]*[。！\n]?', '', content)
        content = re.sub(r'为您撰写以下[：:]?\s*\n?', '', content)
        content = re.sub(r'以下是[^。！\n]*[。！\n]?\s*\n?', '', content)
        # Remove vague legal citations - replace with specific note
        content = re.sub(r'《[^》]+》相关规定', '', content)
        content = re.sub(r'的相关规定', '', content)
        # Remove generic "法律文书" title that LLM sometimes adds
        content = re.sub(r'^法律文书\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'法律文书\s*\n民事', '民事', content)
        # Only replace ID/phone patterns that are NOT part of actual user info lines
        # (user info lines contain "身份证号：" or "电话：" prefix)
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            if '身份证号' in line or '联系电话' in line or '电话：' in line:
                # Don't replace ID/phone in user info lines
                cleaned_lines.append(line)
            else:
                # Replace standalone ID/phone patterns in other lines
                line = re.sub(r'\d{15}(?:\d{2}[\dX])?', '[身份信息已脱敏]', line)
                line = re.sub(r'1[3-9]\d{9}', '[电话已脱敏]', line)
                line = re.sub(r'\d{4}[\dX]{12,}', '[账号已脱敏]', line)
                cleaned_lines.append(line)
        content = '\n'.join(cleaned_lines)

        render_docx_from_text(content, output_path)
        return True
    except Exception as exc:
        ctx.log(f"WARNING: DOCX 渲染失败 {output_path}: {exc}")
        try:
            with open("crash_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"=== DOCX RENDER FAIL: {output_path} ===\n")
                f.write(f"{'='*60}\n")
                f.write(traceback.format_exc())
                f.write("\n")
        except Exception:
            pass
        return False


def _render_xlsx_from_fact_card(
    fact_card,
    output_path: str,
    ctx: PipelineContext,
) -> bool:
    """Render evidence listing to an XLSX file.

    Args:
        fact_card: FactCard with evidence data.
        output_path: Full path for the output XLSX file.
        ctx: PipelineContext for error logging.

    Returns:
        True if rendering succeeded, False otherwise.
    """
    try:
        render_xlsx(fact_card, output_path)
        return True
    except Exception as exc:
        ctx.log(f"WARNING: XLSX 渲染失败 {output_path}: {exc}")
        try:
            with open("crash_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"=== XLSX RENDER FAIL: {output_path} ===\n")
                f.write(f"{'='*60}\n")
                f.write(traceback.format_exc())
                f.write("\n")
        except Exception:
            pass
        return False


def _render_strategy_docx(
    strategy_card,
    doc_type: str,
    output_path: str,
    ctx: PipelineContext,
) -> bool:
    """Render a strategy-related document to DOCX.

    Strategy documents (situation assessment, action advice, evidence gap)
    are constructed from strategy_card fields directly.

    Args:
        strategy_card: StrategyCard with analysis data.
        doc_type: The document type identifier.
        output_path: Full path for the output DOCX file.
        ctx: PipelineContext for error logging.

    Returns:
        True if rendering succeeded, False otherwise.
    """
    content_parts = []

    if doc_type == "案件处境评估报告":
        content_parts.append("案件处境评估报告\n")
        content_parts.append(f"评估等级: {strategy_card.sabcd_rating or '评级生成中'}\n")
        content_parts.append(f"\n{strategy_card.situation_assessment or '案件评估正在进行中，请稍后查看完整报告。'}\n")
        if strategy_card.risk_warnings:
            content_parts.append("\n风险提示:\n")
            for i, warning in enumerate(strategy_card.risk_warnings, 1):
                content_parts.append(f"  {i}. {warning}\n")

    elif doc_type == "行动建议书":
        content_parts.append("行动建议书\n")
        if strategy_card.action_advice:
            for i, advice in enumerate(strategy_card.action_advice, 1):
                content_parts.append(f"\n【建议 {i}】优先级: {advice.priority}\n")
                content_parts.append(f"行动: {advice.action}\n")
                content_parts.append(f"理由: {advice.reasoning}\n")
        else:
            content_parts.append("\n行动建议正在生成中，请稍后查看完整报告。\n")

    elif doc_type == "证据闭环补强清单":
        content_parts.append("证据闭环补强清单\n")
        content_parts.append("\n本清单列明当前案件中需要补充收集的证据材料，以形成完整的证据闭环。\n")
        content_parts.append("建议当事人按照以下清单逐项准备，确保证据链完整、逻辑清晰。\n")
        if strategy_card.evidence_gap:
            content_parts.append("\n一、需要收集的证据清单\n")
            for i, gap in enumerate(strategy_card.evidence_gap, 1):
                content_parts.append(f"\n  {i}. {gap}\n")
                content_parts.append(f"     重要程度: 高\n")
                content_parts.append(f"     建议获取方式: 当事人提供或调查取证\n")
            content_parts.append(f"\n二、证据收集建议\n")
            content_parts.append("1. 所有证据应保留原件或经公证的复印件\n")
            content_parts.append("2. 电子证据应注意保全公证\n")
            content_parts.append("3. 证人证言应提前沟通并取得书面确认\n")
            content_parts.append("4. 涉及专业问题可申请鉴定\n")
        else:
            content_parts.append("\n当前证据较为完整，建议定期复查证据状态，确保持续有效。\n")

    else:
        content_parts.append(f"{doc_type}\n")
        content_parts.append(f"\n本文书由明证台V18系统自动生成，仅供参考。\n")
        content_parts.append("正式提交前请务必由专业律师审核修改。\n")
        content_parts.append("\n一、文书说明\n")
        content_parts.append(f"本文书为{ctx.identity}在{ctx.goal}场景下的法律文书草稿。\n")
        content_parts.append("系统根据案件材料自动分析生成，旨在提供文书框架和基础内容。\n")
        content_parts.append("\n二、注意事项\n")
        content_parts.append("1. 请仔细核对当事人信息是否准确\n")
        content_parts.append("2. 请核实案件事实和金额数据\n")
        content_parts.append("3. 请补充完善证据引用和法律依据\n")
        content_parts.append("4. 请根据实际情况调整诉讼请求\n")
        content_parts.append("\n三、免责声明\n")
        content_parts.append("本系统提供的文书草稿不构成法律意见。\n")
        content_parts.append("当事人应自行承担使用本文书的风险。\n")
        content_parts.append("建议在正式提交前咨询专业律师。\n")

    full_content = "".join(content_parts)
    return _render_docx_from_content(full_content, output_path, ctx)


def _render_draft_documents(
    strategy_card,
    output_path: str,
    ctx: PipelineContext,
) -> bool:
    """Render draft documents to a DOCX file.

    Combines all draft documents from the strategy card into a single file.
    When draft_documents is empty, generates a structured legal document
    template using fact_card data and strategy analysis, similar to MIMO's
    workflow output.

    Args:
        strategy_card: StrategyCard with draft document data.
        output_path: Full path for the output DOCX file.
        ctx: PipelineContext for error logging.

    Returns:
        True if rendering succeeded, False otherwise.
    """
    if not strategy_card or not strategy_card.draft_documents:
        fc = getattr(ctx, 'fact_card', None)
        identity = getattr(ctx, 'identity', '') or ''
        goal = getattr(ctx, 'goal', '') or ''

        # Extract user info from source_refs
        user_info = _extract_user_info_from_refs(fc) if fc else {}

        content_parts = []

        def _is_company(name: str) -> bool:
            """判断当事人是否为公司法人。"""
            return any(kw in name for kw in ('公司', '有限', '集团', '企业', '工厂', '商行', '商店', '事务所'))

        # Build structured legal document based on identity
        if '被告' in identity or '被诉' in identity:
            content_parts.append("民事答辩状\n\n")
            # Party info from fact_card with detailed info
            if fc and fc.parties:
                defendants = [p for p in fc.parties if p.role in ('被告', '被上诉人')]
                plaintiffs = [p for p in fc.parties if p.role in ('原告', '上诉人')]
                for d in defendants:
                    if _is_company(d.name):
                        content_parts.append(
                            f"答辩人（被告）：{d.name}\n"
                            f"住所地：____\n"
                            f"统一社会信用代码：____\n"
                            f"法定代表人：____，职务：____\n"
                        )
                    else:
                        ui = user_info.get(d.name, {})
                        content_parts.append(
                            f"答辩人（被告）：{d.name}，{ui.get('gender', '____')}，"
                            f"{ui.get('birth', '____年____月____日')}出生，"
                            f"{ui.get('ethnicity', '汉族')}，"
                            f"住{ui.get('address', '____')}"
                            f"，身份证号：{ui.get('id_number', '____')}"
                            f"，联系电话：{ui.get('phone', '____')}\n"
                        )
                for p in plaintiffs:
                    if _is_company(p.name):
                        content_parts.append(
                            f"被答辩人（原告）：{p.name}\n"
                            f"住所地：____\n"
                            f"法定代表人：____\n"
                        )
                    else:
                        ui = user_info.get(p.name, {})
                        content_parts.append(
                            f"被答辩人（原告）：{p.name}，{ui.get('gender', '____')}，"
                            f"{ui.get('birth', '____年____月____日')}出生，"
                            f"{ui.get('ethnicity', '汉族')}，"
                            f"住{ui.get('address', '____')}"
                            f"，身份证号：{ui.get('id_number', '____')}"
                            f"，联系电话：{ui.get('phone', '____')}\n"
                        )
            content_parts.append(f"\n案号：{fc.case_id if fc and fc.case_id else '待补充'}\n")
            content_parts.append(f"案由：{_derive_case_type(fc)}\n\n")

            content_parts.append("答辩请求：\n")
            content_parts.append("1. 请求依法驳回被答辩人的全部或部分诉讼请求\n")
            content_parts.append("2. 请求依法判决本案诉讼费用由被答辩人承担\n\n")

            content_parts.append("事实与理由：\n\n")
            if fc and fc.key_facts:
                content_parts.append("一、案件基本情况\n")
                for i, fact in enumerate(fc.key_facts[:6], 1):
                    clean = fact.replace("【待核对】", "").replace("【争议】", "").strip()
                    if clean:
                        content_parts.append(f"{i}. {clean}\n")
                content_parts.append("\n")

            content_parts.append("法律依据：\n")
            content_parts.append("1. 《中华人民共和国民事诉讼法》第一百二十五条（答辩状提交）\n")
            content_parts.append("2. 《中华人民共和国民法典》第四百六十五条（合同效力）\n")
            content_parts.append("3. 《中华人民共和国民事诉讼法》第六十七条（举证责任）\n\n")

            content_parts.append("综上所述，答辩人的答辩意见合法有据，请贵院依法审查并采纳。\n\n")
            content_parts.append(f"此致\n{fc.court if fc and fc.court else '________人民法院'}\n\n")
            content_parts.append("答辩人：_______________\n")
            content_parts.append("日期：_______________\n")

        elif '原告' in identity or '起诉' in identity:
            content_parts.append("民事起诉状\n\n")
            if fc and fc.parties:
                plaintiffs = [p for p in fc.parties if p.role in ('原告', '上诉人')]
                defendants = [p for p in fc.parties if p.role in ('被告', '被上诉人')]
                if plaintiffs:
                    content_parts.append(f"原告：{plaintiffs[0].name}\n")
                if defendants:
                    content_parts.append(f"被告：{defendants[0].name}\n")
            content_parts.append(f"\n案由：{_derive_case_type(fc)}\n\n")
            content_parts.append("诉讼请求：\n")
            content_parts.append(f"1. 判令被告向原告支付{'人民币' + fc.amount if fc and fc.amount else '相应款项'}\n")
            content_parts.append("2. 判令被告承担本案全部诉讼费用\n\n")
            content_parts.append("事实与理由：\n\n")
            if fc and fc.key_facts:
                for i, fact in enumerate(fc.key_facts[:6], 1):
                    clean = fact.replace("【待核对】", "").replace("【争议】", "").strip()
                    if clean:
                        content_parts.append(f"{i}. {clean}\n")
            content_parts.append("\n综上所述，原告的诉讼请求合法有据，恳请贵院依法支持。\n\n")
            content_parts.append(f"此致\n{fc.court if fc and fc.court else '________人民法院'}\n\n")
            content_parts.append("具状人：_______________\n")
            content_parts.append("日期：_______________\n")

        else:
            # Generic fallback - use strategy data
            content_parts.append("法律文书草稿\n\n")
            if strategy_card.situation_assessment:
                content_parts.append(f"一、案件评估\n{strategy_card.situation_assessment}\n\n")
            if strategy_card.action_advice:
                content_parts.append("二、行动建议\n")
                for i, advice in enumerate(strategy_card.action_advice, 1):
                    content_parts.append(f"{i}. [{advice.priority}] {advice.action}\n")
            if strategy_card.evidence_gap:
                content_parts.append("\n三、证据补强\n")
                for i, gap in enumerate(strategy_card.evidence_gap, 1):
                    content_parts.append(f"{i}. {gap}\n")
            if strategy_card.risk_warnings:
                content_parts.append("\n四、风险提示\n")
                for i, w in enumerate(strategy_card.risk_warnings, 1):
                    content_parts.append(f"{i}. {w}\n")

        content = "".join(content_parts)
    else:
        parts = []
        for i, draft in enumerate(strategy_card.draft_documents, 1):
            if i > 1:
                parts.append(f"\n\n{'='*60}\n\n")
            parts.append(draft.content or "")
        content = "".join(parts)

    return _render_docx_from_content(content, output_path, ctx)


def _derive_case_type(fc) -> str:
    """Derive case type (案由) from fact card data."""
    if not fc:
        return "待补充"
    # Collect all text for keyword matching
    all_text = " ".join(fc.key_facts or []) + " " + " ".join(fc.disputed_facts or [])
    case_id = (fc.case_id or "").lower()
    # Check for specific case types
    if "中介" in all_text or "中介" in case_id:
        return "中介合同纠纷"
    if "借款" in all_text or "借贷" in all_text or "垫资" in all_text:
        return "民间借贷纠纷"
    if "买卖" in all_text:
        return "买卖合同纠纷"
    if "租赁" in all_text:
        return "租赁合同纠纷"
    if "劳动" in all_text or "工伤" in all_text:
        return "劳动争议"
    if "合同" in all_text or "协议" in all_text:
        return "合同纠纷"
    if "侵权" in all_text:
        return "侵权责任纠纷"
    return "民事纠纷"


def _extract_user_info_from_refs(fc) -> dict:
    """Extract detailed user info from fact_card source_refs.

    Only extracts info for the DEFENDANT from defendant-specific documents.
    Plaintiff info is NOT extracted to avoid data contamination.
    """
    import re
    info = {}
    if not fc or not fc.source_refs or not fc.parties:
        return info

    # Only extract info for defendants
    defendant_names = [p.name for p in fc.parties if p.role in ('被告', '被上诉人') and p.name]
    if not defendant_names:
        return info

    for ref in fc.source_refs:
        excerpt = ref.excerpt or ""
        # Only process excerpts that are clearly about the defendant
        # (e.g., defendant's own applications, not court documents listing all parties)
        is_defendant_doc = False
        for dname in defendant_names:
            # Check if this is a document filed BY the defendant (not just mentioning them)
            if f"申请人：{dname}" in excerpt or f"答辩人：{dname}" in excerpt or f"提交人：{dname}" in excerpt:
                is_defendant_doc = True
                break
        if not is_defendant_doc:
            continue

        for dname in defendant_names:
            if dname in excerpt:
                if dname not in info:
                    info[dname] = {}
                # Search the full excerpt for personal info
                m = re.search(r'([男女])', excerpt)
                if m:
                    info[dname]['gender'] = m.group(1)
                m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日出生', excerpt)
                if m:
                    info[dname]['birth'] = f"{m.group(1)}年{m.group(2)}月{m.group(3)}日"
                m = re.search(r'住([^\s，,。；]+)', excerpt)
                if m:
                    info[dname]['address'] = m.group(1)
                m = re.search(r'身份证号[：:]?\s*(\d{17}[\dX])', excerpt)
                if m:
                    info[dname]['id_number'] = m.group(1)
                m = re.search(r'(?:电话|联系电话)[：:]?\s*(1[3-9]\d{9})', excerpt)
                if m:
                    info[dname]['phone'] = m.group(1)
    return info


def _get_party_name(ctx: PipelineContext) -> str:
    """从上下文中提取主要当事人姓名用于动态文件名。"""
    fc = ctx.fact_card
    if not fc or not fc.parties:
        return ""
    for p in fc.parties:
        if p.role and "被告" in p.role and p.name:
            return p.name
    for p in fc.parties:
        if p.role and "原告" in p.role and p.name:
            return p.name
    return fc.parties[0].name if fc.parties[0].name else ""


def _make_filename(prefix: str, fmt: str, ctx: PipelineContext, doc_type: str = "") -> str:
    """动态文件名：06_答辩状_程颖颖案.docx"""
    party = _get_party_name(ctx)
    suffix = f"_{party}案" if party else ""
    if doc_type:
        return f"{prefix}_{doc_type}{suffix}.{fmt}"
    return f"{prefix}{suffix}.{fmt}"


def step7_render(ctx: PipelineContext) -> PipelineContext:
    """Render all documents and build the customer delivery package.

    优先使用 LLM 生成的文书内容（step6_llm_generate），降级到模板填充。
    动态文件名：从上下文提取当事人姓名。

    Args:
        ctx: PipelineContext with _llm_generated_docs / _filled_templates.

    Returns:
        PipelineContext with rendered files in output_dir/customer/.
    """
    from core.pipeline.step7_render_manifest import render_with_manifest

    ctx.log("Step 7: 文档渲染 - 生成交付文档并打包")

    try:
        from core.task_store import get_task_store
        ts = get_task_store()
    except Exception:
        ts = None

    task_id = getattr(ctx, "task_id", "")

    llm_docs: Dict[str, str] = getattr(ctx, "_llm_generated_docs", {})
    filled_templates: Dict[str, str] = getattr(ctx, "_filled_templates", {})
    customer_dir: str = getattr(ctx, "_customer_dir", "")

    # --- 后处理蒸馏：对LLM生成的文书进行蒸馏优化 ---
    if llm_docs:
        from core.pipeline.step7_postprocess import postprocess_documents
        llm_docs = postprocess_documents(ctx)
        ctx._llm_generated_docs = llm_docs  # type: ignore[attr-defined]
        ctx.log(f"  后处理蒸馏完成: {len(llm_docs)} 份文书")
        # Debug: 检查后处理结果
        for doc_type, content in llm_docs.items():
            if '答辩状' in doc_type:
                ctx.log(f"  答辩状后处理检查: 住址={('赣州市' in content)}, 律师费论点={('人为扩大' in content)}")

    if not customer_dir:
        customer_dir = os.path.join(ctx.output_dir, "customer")
        os.makedirs(customer_dir, exist_ok=True)
        ctx._customer_dir = customer_dir  # type: ignore[attr-defined]

    if not llm_docs and not filled_templates:
        ctx.add_error("无文书内容可渲染（_llm_generated_docs 和 _filled_templates 均为空）")
        return ctx

    rendered_files: List[str] = []
    failed_files: List[str] = []
    pdf_files: List[str] = []

    # --- Render standard documents (01-05) ---
    for file_prefix, doc_type, fmt in DOCUMENT_ORDER:
        # 动态文件名
        file_name = _make_filename(file_prefix, fmt, ctx)
        output_path = os.path.join(customer_dir, file_name)

        content = llm_docs.get(doc_type) or filled_templates.get(doc_type)

        if doc_type == "证据目录" and ctx.fact_card:
            render_fn = lambda op=output_path, fc=ctx.fact_card: _render_xlsx_from_fact_card(fc, op, ctx)
        elif doc_type == "可提交文书草稿" and ctx.strategy_card:
            render_fn = lambda op=output_path, sc=ctx.strategy_card: _render_draft_documents(sc, op, ctx)
        elif content:
            render_fn = lambda op=output_path, c=content: _render_docx_from_content(c, op, ctx)
        elif ctx.strategy_card and doc_type in ("案件处境评估报告", "行动建议书", "证据闭环补强清单"):
            render_fn = lambda op=output_path, sc=ctx.strategy_card, dt=doc_type: _render_strategy_docx(sc, dt, op, ctx)
        else:
            ctx.log(f"WARNING: 跳过 {doc_type} - 无可用数据")
            if ts and task_id:
                ts.manifest_init_entry(task_id, file_name, fmt)
                ts.manifest_mark_skipped(task_id, file_name, "无可用数据")
                try:
                    from core.audit_store import log_manifest_skipped
                    log_manifest_skipped(task_id, file_name, "无可用数据")
                except Exception:
                    pass
            continue

        success = render_with_manifest(
            ctx, task_id, file_name, fmt, render_fn, output_path, ts=ts,
        )

        if success:
            rendered_files.append(output_path)
            if fmt == "docx":
                pdf_name = file_name.replace(".docx", ".pdf")
                pdf_path = output_path.replace(".docx", ".pdf")
                pdf_render_fn = lambda dp=pdf_path, sp=output_path: convert_to_pdf(sp, dp)
                pdf_success = render_with_manifest(
                    ctx, task_id, pdf_name, "pdf", pdf_render_fn, pdf_path,
                    source_file=output_path, ts=ts,
                )
                if pdf_success:
                    pdf_files.append(pdf_path)
                    rendered_files.append(pdf_path)
                else:
                    failed_files.append(pdf_name)
        else:
            failed_files.append(file_name)

    # --- Render identity-specific extra document ---
    extra_doc = _get_identity_extra_doc(ctx.identity)
    if extra_doc:
        extra_prefix, extra_type, extra_fmt = extra_doc
        extra_name = _make_filename(extra_prefix, extra_fmt, ctx)
        extra_path = os.path.join(customer_dir, extra_name)

        content = llm_docs.get(extra_type) or filled_templates.get(extra_type)
        if content:
            extra_render_fn = lambda op=extra_path, c=content: _render_docx_from_content(c, op, ctx)
            success = render_with_manifest(
                ctx, task_id, extra_name, extra_fmt, extra_render_fn, extra_path, ts=ts,
            )
            if success:
                rendered_files.append(extra_path)
                pdf_name = extra_name.replace(".docx", ".pdf")
                pdf_path = extra_path.replace(".docx", ".pdf")
                pdf_render_fn = lambda dp=pdf_path, sp=extra_path: convert_to_pdf(sp, dp)
                pdf_success = render_with_manifest(
                    ctx, task_id, pdf_name, "pdf", pdf_render_fn, pdf_path,
                    source_file=extra_path, ts=ts,
                )
                if pdf_success:
                    pdf_files.append(pdf_path)
                    rendered_files.append(pdf_path)
                else:
                    failed_files.append(pdf_name)
            else:
                failed_files.append(extra_name)

    # --- Build customer delivery ZIP ---
    zip_name = "客户交付包.zip"
    zip_path = os.path.join(customer_dir, zip_name)
    zip_render_fn = lambda: build_zip(customer_dir, zip_path)
    zip_success = render_with_manifest(
        ctx, task_id, zip_name, "zip", zip_render_fn, zip_path, ts=ts,
    )
    if not zip_success:
        # Try manual fallback
        manual_fn = lambda: _manual_build_zip(customer_dir, zip_path)
        zip_success = render_with_manifest(
            ctx, task_id, zip_name, "zip", manual_fn, zip_path, ts=ts,
        )
    if zip_success:
        rendered_files.append(zip_path)

    # Store rendered file list for quality gate
    ctx._rendered_files = rendered_files  # type: ignore[attr-defined]
    ctx._render_failed_files = failed_files  # type: ignore[attr-defined]

    # ── Business fallback: save distilled_card as plain text if all rendering failed ──
    if not rendered_files and ctx.distilled_card:
        fallback_path = os.path.join(customer_dir, "最终分析报告_纯文本版.txt")
        try:
            _save_distilled_card_as_text(ctx.distilled_card, fallback_path, ctx)
            rendered_files.append(fallback_path)
            ctx._rendered_files = rendered_files  # type: ignore[attr-defined]
            ctx.log(f"  业务兜底: 已保存纯文本版报告 {fallback_path}")
        except Exception as exc:
            ctx.log(f"  业务兜底失败: {exc}")

    total = len(rendered_files)
    docx_count = sum(1 for f in rendered_files if f.endswith(".docx"))
    pdf_count = len(pdf_files)
    xlsx_count = sum(1 for f in rendered_files if f.endswith(".xlsx"))
    zip_count = 1 if any(f.endswith(".zip") for f in rendered_files) else 0

    ctx.log(
        f"Step 7 完成: 渲染 {docx_count} DOCX + {xlsx_count} XLSX + "
        f"{pdf_count} PDF + {zip_count} ZIP = {total} 个文件"
    )

    if failed_files:
        ctx.log(f"  失败文件: {len(failed_files)} 个")
        for f in failed_files:
            ctx.log(f"    - {f}")

    return ctx


def _manual_build_zip(source_dir: str, zip_path: str) -> None:
    """Manual ZIP builder as fallback when core.render.zip_builder fails.

    Walks the source directory and adds all files to a ZIP archive.

    Args:
        source_dir: Directory containing files to zip.
        zip_path: Output path for the ZIP file.
    """
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(source_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                arcname = os.path.relpath(file_path, source_dir)
                zf.write(file_path, arcname)


def _save_distilled_card_as_text(distilled_card, output_path: str, ctx: PipelineContext) -> None:
    """Save distilled_card content as a plain text file for business fallback.

    This ensures users always get the AI analysis results even if DOCX rendering fails.

    Args:
        distilled_card: The DistilledCard with fact_card and strategy_card.
        output_path: Path to save the text file.
        ctx: PipelineContext for logging.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("明证台 V18 - 最终分析报告（纯文本版）")
    lines.append("=" * 60)
    lines.append("")

    fc = distilled_card.fact_card
    sc = distilled_card.strategy_card

    if fc:
        lines.append("【案件事实信息】")
        lines.append("-" * 40)
        if fc.case_id:
            lines.append(f"案件编号: {fc.case_id}")
        if fc.court:
            lines.append(f"管辖法院: {fc.court}")
        if fc.identity:
            lines.append(f"当事人身份: {fc.identity}")
        if fc.amount:
            lines.append(f"涉及金额: {fc.amount}")
        if fc.deadline:
            lines.append(f"关键期限: {fc.deadline}")
        lines.append("")

        if fc.parties:
            lines.append("当事人信息:")
            for p in fc.parties:
                lines.append(f"  {p.role}: {p.name}")
            lines.append("")

        if fc.key_facts:
            lines.append("核心事实:")
            for i, fact in enumerate(fc.key_facts, 1):
                lines.append(f"  {i}. {fact}")
            lines.append("")

        if fc.disputed_facts:
            lines.append("争议事实:")
            for i, fact in enumerate(fc.disputed_facts, 1):
                lines.append(f"  {i}. {fact}")
            lines.append("")

        if fc.conflicts:
            lines.append("事实冲突:")
            for i, conflict in enumerate(fc.conflicts, 1):
                lines.append(f"  {i}. {conflict}")
            lines.append("")

        if fc.missing_materials:
            lines.append("缺失材料:")
            for i, material in enumerate(fc.missing_materials, 1):
                lines.append(f"  {i}. {material}")
            lines.append("")

    if sc:
        lines.append("")
        lines.append("【法律策略分析】")
        lines.append("-" * 40)
        if sc.sabcd_rating:
            lines.append(f"综合评级: {sc.sabcd_rating}")
        if sc.situation_assessment:
            lines.append(f"处境评估: {sc.situation_assessment}")
        lines.append("")

        if sc.action_advice:
            lines.append("行动建议:")
            for i, advice in enumerate(sc.action_advice, 1):
                priority = advice.priority or "待定"
                lines.append(f"  {i}. [{priority}] {advice.action}")
                if advice.reasoning:
                    lines.append(f"     理由: {advice.reasoning}")
            lines.append("")

        if sc.evidence_gap:
            lines.append("证据缺口:")
            for i, gap in enumerate(sc.evidence_gap, 1):
                lines.append(f"  {i}. {gap}")
            lines.append("")

        if sc.risk_warnings:
            lines.append("风险提示:")
            for i, warning in enumerate(sc.risk_warnings, 1):
                lines.append(f"  {i}. {warning}")
            lines.append("")

        if sc.draft_documents:
            lines.append("")
            lines.append("【文书草稿】")
            lines.append("-" * 40)
            for i, draft in enumerate(sc.draft_documents, 1):
                lines.append(f"文书 {i}: {draft.title or draft.doc_type}")
                if draft.content:
                    lines.append(draft.content)
                lines.append("")

    lines.append("")
    lines.append("=" * 60)
    lines.append("本报告由明证台V18系统自动生成，仅供参考。")
    lines.append("建议结合专业律师意见做出最终决策。")
    lines.append("=" * 60)

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
