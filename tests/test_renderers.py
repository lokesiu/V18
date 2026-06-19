"""Tests for document renderers."""
import pytest
import sys
import os
sys.path.insert(0, "D:\\codex\\V18")


def test_docx_renderer(tmp_path):
    from core.render.docx_renderer import render_docx
    output = str(tmp_path / "test.docx")
    sections = [
        {
            "heading": "测试标题",
            "content": "这是一个测试文档，用于验证DOCX生成功能是否正常工作。包含足够的中文字符。"
        }
    ]
    assert render_docx("测试文档", sections, output) == True
    assert os.path.exists(output)
    assert os.path.getsize(output) > 0


def test_xlsx_renderer(tmp_path):
    from core.render.xlsx_renderer import render_evidence_catalog
    from core.fact_card import FactCard, SourceRef
    fc = FactCard(
        key_facts=["事实1", "事实2", "事实3"],
        source_refs=[SourceRef(file_name="test.pdf", excerpt="摘要1")]
    )
    output = str(tmp_path / "test.xlsx")
    assert render_evidence_catalog(fc, output) == True
    assert os.path.exists(output)
