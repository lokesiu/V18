"""
tests/test_defense_doc_not_generic.py

Test: Defense document must be case-specific, not generic.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, ".")


def _get_customer_dir():
    """Get the golden case customer directory."""
    return "outputs/golden_defense_case/customer"


def _read_docx_text(docx_path: str) -> str:
    """Read all text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(docx_path)
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        return "\n".join(parts)
    except Exception:
        return ""


def test_defense_doc_exists():
    """Defense document must exist."""
    customer_dir = _get_customer_dir()
    if not os.path.isdir(customer_dir):
        return

    defense_files = list(Path(customer_dir).glob("*答辩*.docx"))
    assert len(defense_files) > 0, "No defense document found"


def test_defense_doc_contains_case_keywords():
    """Defense document must contain case-specific keywords."""
    customer_dir = _get_customer_dir()
    if not os.path.isdir(customer_dir):
        return

    defense_files = list(Path(customer_dir).glob("*答辩*.docx"))
    if not defense_files:
        return

    # Keywords that must appear in a defense for 借款纠纷
    required_keywords = [
        "本金",  # Must discuss principal amount
        "利息",  # Must discuss interest
        "借款协议",  # Must reference the loan agreement
        "银行转账",  # Must reference bank transfer
    ]

    for docx_path in defense_files:
        text = _read_docx_text(str(docx_path))
        missing = []
        for keyword in required_keywords:
            if keyword not in text:
                missing.append(keyword)
        assert not missing, f"{docx_path.name} missing keywords: {missing}"


def test_defense_doc_contains_party_names():
    """Defense document must contain actual party names."""
    customer_dir = _get_customer_dir()
    if not os.path.isdir(customer_dir):
        return

    defense_files = list(Path(customer_dir).glob("*答辩*.docx"))
    if not defense_files:
        return

    for docx_path in defense_files:
        text = _read_docx_text(str(docx_path))
        # For Golden Case: 张三 (plaintiff) and 李四 (defendant)
        assert "张三" in text, f"{docx_path.name} should mention plaintiff '张三'"
        assert "李四" in text, f"{docx_path.name} should mention defendant '李四'"


def test_defense_doc_contains_court_name():
    """Defense document must contain the court name."""
    customer_dir = _get_customer_dir()
    if not os.path.isdir(customer_dir):
        return

    defense_files = list(Path(customer_dir).glob("*答辩*.docx"))
    if not defense_files:
        return

    for docx_path in defense_files:
        text = _read_docx_text(str(docx_path))
        assert "朝阳" in text or "法院" in text, \
            f"{docx_path.name} should mention the court"


def test_defense_doc_not_too_short():
    """Defense document must have sufficient content."""
    customer_dir = _get_customer_dir()
    if not os.path.isdir(customer_dir):
        return

    defense_files = list(Path(customer_dir).glob("*答辩*.docx"))
    if not defense_files:
        return

    for docx_path in defense_files:
        text = _read_docx_text(str(docx_path))
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        assert chinese_count >= 500, \
            f"{docx_path.name} too short: {chinese_count} Chinese chars (need >= 500)"
