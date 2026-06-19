"""
tests/test_expected_file_list_v18_rc.py

Test: Expected file list matches V18-RC current naming.
"""
import sys

sys.path.insert(0, ".")


def test_expected_docx_names_are_v18_rc():
    """EXPECTED_DOCX_NAMES must use V18-RC naming convention."""
    from core.quality.final_artifact_auditor import EXPECTED_DOCX_NAMES

    v18_rc_names = [
        "01_案件处境评估报告.docx",
        "02_行动建议书.docx",
        "03_证据闭环补强清单.docx",
        "05_可提交文书草稿.docx",
        "06_答辩状.docx",
    ]

    assert EXPECTED_DOCX_NAMES == v18_rc_names, \
        f"Expected {v18_rc_names}, got {EXPECTED_DOCX_NAMES}"


def test_legacy_names_not_in_expected():
    """Legacy names must NOT be in EXPECTED_DOCX_NAMES."""
    from core.quality.final_artifact_auditor import EXPECTED_DOCX_NAMES

    legacy_names = [
        "事实与证据清单.docx",
        "法律分析报告.docx",
        "策略建议书.docx",
        "起诉状.docx",
        "证据目录.docx",
    ]

    for name in legacy_names:
        assert name not in EXPECTED_DOCX_NAMES, \
            f"Legacy name '{name}' should not be in EXPECTED_DOCX_NAMES"


def test_legacy_names_defined_separately():
    """Legacy names should be defined in LEGACY_DOCX_NAMES for reference."""
    from core.quality.final_artifact_auditor import LEGACY_DOCX_NAMES

    assert len(LEGACY_DOCX_NAMES) == 5, "Should have 5 legacy names"
    assert "起诉状.docx" in LEGACY_DOCX_NAMES, "Legacy should include 起诉状.docx"
