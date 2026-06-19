"""
pdf_converter.py - PDF 转换引擎

优先级：
1. docx2pdf (Windows Word COM) — 最高质量，保留全部格式
2. LibreOffice headless — 跨平台高质量
3. reportlab — 专业级 PDF 生成，支持中文排版
"""
from __future__ import annotations

import os
import re
import logging
import subprocess
import shutil

logger = logging.getLogger(__name__)

FONT_SIMSUN_TTC = r"C:\Windows\Fonts\simsun.ttc"
FONT_SIMHEI_TTF = r"C:\Windows\Fonts\simhei.ttf"
FONT_FANGSONG_TTF = r"C:\Windows\Fonts\fsong.ttf"


def convert_to_pdf(docx_path: str, pdf_path: str) -> bool:
    """将 DOCX 转换为 PDF。优先使用 reportlab 保证标题居中。"""
    if not os.path.exists(docx_path):
        logger.error("DOCX file not found: %s", docx_path)
        return False

    # 优先使用 reportlab 保证中文排版和标题居中
    if _try_reportlab(docx_path, pdf_path):
        return True
    # 降级到 docx2pdf
    if _try_docx2pdf(docx_path, pdf_path):
        return True
    if _try_libreoffice(docx_path, pdf_path):
        return True

    logger.error("All PDF conversion strategies failed for: %s", docx_path)
    return False


def _try_docx2pdf(docx_path: str, pdf_path: str) -> bool:
    try:
        from docx2pdf import convert as d2p_convert
        d2p_convert(docx_path, pdf_path)
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 100:
            logger.info("PDF via docx2pdf (Word COM): %s", pdf_path)
            return True
    except (ImportError, Exception):
        pass
    return False


def _try_libreoffice(docx_path: str, pdf_path: str) -> bool:
    lo_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        shutil.which("soffice") or "",
    ]
    for lo_exe in lo_paths:
        if not lo_exe or not os.path.exists(lo_exe):
            continue
        try:
            output_dir = os.path.dirname(pdf_path) or "."
            subprocess.run(
                [lo_exe, "--headless", "--convert-to", "pdf", "--outdir", output_dir, docx_path],
                capture_output=True, timeout=60,
            )
            expected = os.path.join(output_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
            if os.path.exists(expected) and os.path.getsize(expected) > 100:
                if expected != pdf_path:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    os.rename(expected, pdf_path)
                logger.info("PDF via LibreOffice: %s", pdf_path)
                return True
        except Exception:
            pass
    return False


def _try_reportlab(docx_path: str, pdf_path: str) -> bool:
    """使用 reportlab 生成专业级 PDF（从 DOCX 提取文本并排版）。"""
    try:
        from docx import Document as DocxDocument
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as e:
        logger.debug("reportlab or python-docx not available: %s", e)
        return False

    # Register Chinese font
    font_name = "Helvetica"
    for fp, name in [(FONT_SIMHEI_TTF, "SimHei"), (FONT_SIMSUN_TTC, "SimSun"), (FONT_FANGSONG_TTF, "FangSong")]:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont(name, fp))
                font_name = name
                break
            except Exception:
                continue

    try:
        doc = DocxDocument(docx_path)
        os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)

        pdf_doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            topMargin=3.7*cm,
            bottomMargin=3.5*cm,
            leftMargin=2.8*cm,
            rightMargin=2.6*cm,
        )

        # Styles
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            'CnTitle', parent=styles['Title'],
            fontName=font_name, fontSize=18, leading=24,
            alignment=TA_CENTER, spaceAfter=12,
        )
        style_h1 = ParagraphStyle(
            'CnH1', parent=styles['Heading1'],
            fontName=font_name, fontSize=14, leading=20,
            spaceBefore=12, spaceAfter=6,
        )
        style_h2 = ParagraphStyle(
            'CnH2', parent=styles['Heading2'],
            fontName=font_name, fontSize=12, leading=16,
            spaceBefore=8, spaceAfter=4,
        )
        style_body = ParagraphStyle(
            'CnBody', parent=styles['Normal'],
            fontName=font_name, fontSize=11, leading=18,
            alignment=TA_JUSTIFY, firstLineIndent=22,
            spaceBefore=2, spaceAfter=2,
        )
        style_body_no_indent = ParagraphStyle(
            'CnBodyNoIndent', parent=style_body,
            firstLineIndent=0,
        )

        # Build story
        story = []
        title_found = False

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                story.append(Spacer(1, 6))
                continue

            # Clean markdown
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
            text = re.sub(r'^#{1,6}\s+', '', text)
            text = re.sub(r'^\s*[-*]\s+', '', text)

            # Escape XML entities for reportlab
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            style_name = para.style.name if para.style else ""
            
            # Check if paragraph is centered in DOCX
            is_centered = False
            if para.alignment is not None:
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                is_centered = (para.alignment == WD_ALIGN_PARAGRAPH.CENTER)

            # First non-empty paragraph: always treat as title
            if not title_found:
                story.append(Paragraph(text, style_title))
                title_found = True
            elif is_centered:
                # Other centered paragraphs also get title style
                story.append(Paragraph(text, style_title))
            elif 'Heading 1' in style_name or '标题 1' in style_name:
                story.append(Spacer(1, 8))
                story.append(Paragraph(text, style_h1))
            elif 'Heading 2' in style_name or '标题 2' in style_name:
                story.append(Paragraph(text, style_h2))
            elif 'Heading' in style_name:
                story.append(Paragraph(text, style_h1))
            else:
                story.append(Paragraph(text, style_body))

        if not story:
            story.append(Paragraph("法律文书", style_title))

        pdf_doc.build(story)

        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 100:
            logger.info("PDF via reportlab: %s", pdf_path)
            return True

    except Exception as exc:
        logger.error("reportlab conversion failed: %s", exc)
    return False


def render_pdf_from_text(title: str, content: str, output_path: str) -> bool:
    """直接从文本渲染 PDF（reportlab）。"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return False

    font_name = "Helvetica"
    for fp, name in [(FONT_SIMHEI_TTF, "SimHei"), (FONT_SIMSUN_TTC, "SimSun")]:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont(name, fp))
                font_name = name
                break
            except Exception:
                continue

    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        pdf_doc = SimpleDocTemplate(output_path, pagesize=A4,
                                    topMargin=3.7*cm, bottomMargin=3.5*cm,
                                    leftMargin=2.8*cm, rightMargin=2.6*cm)
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle('T', fontName=font_name, fontSize=18, leading=24, alignment=TA_CENTER, spaceAfter=12)
        style_body = ParagraphStyle('B', fontName=font_name, fontSize=11, leading=18, alignment=TA_JUSTIFY, firstLineIndent=22)

        story = [Paragraph(title or "法律文书", style_title)]
        for line in (content or "").split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
            else:
                line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(line, style_body))

        pdf_doc.build(story)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 100
    except Exception as exc:
        logger.error("reportlab text render failed: %s", exc)
        return False
