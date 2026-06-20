"""TDD tests for core/quality/defense_quality_gate.py — branch coverage."""
import pytest
import sys, os, json, zipfile
sys.path.insert(0, ".")

from pathlib import Path
from core.quality.defense_quality_gate import DefenseQualityGate
from core.contracts.quality_gate import CheckSeverity


class TestDefenseQualityGate:
    def _make_gate(self):
        return DefenseQualityGate()

    def _make_case(self, tmp_path, identity="被诉方（被告）"):
        """Create a minimal case directory structure."""
        customer = tmp_path / "customer"
        internal = tmp_path / "_internal"
        customer.mkdir()
        internal.mkdir()
        return tmp_path, customer, internal


# ══════════════════════════════════════════════════════════════════════
# _check_ai_mode
# ══════════════════════════════════════════════════════════════════════
class TestCheckAiMode:
    def test_real_ai_passes(self):
        gate = DefenseQualityGate()
        check = gate._check_ai_mode("real_ai")
        assert check.passed is True
        assert "real_ai" in check.message

    def test_mixed_passes(self):
        gate = DefenseQualityGate()
        check = gate._check_ai_mode("mixed")
        assert check.passed is True

    def test_local_fallback_fails(self):
        gate = DefenseQualityGate()
        check = gate._check_ai_mode("local_fallback")
        assert check.passed is False
        assert check.severity == CheckSeverity.CRITICAL

    def test_unknown_passes(self):
        gate = DefenseQualityGate()
        check = gate._check_ai_mode("unknown")
        assert check.passed is True


# ══════════════════════════════════════════════════════════════════════
# _check_pdf_exists
# ══════════════════════════════════════════════════════════════════════
class TestCheckPdfExists:
    def test_no_pdfs_fails(self, tmp_path):
        gate = DefenseQualityGate()
        check = gate._check_pdf_exists(str(tmp_path))
        assert check.passed is False

    def test_with_pdf_passes(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"%PDF fake")
        gate = DefenseQualityGate()
        check = gate._check_pdf_exists(str(tmp_path))
        assert check.passed is True

    def test_nonexistent_dir_fails(self):
        gate = DefenseQualityGate()
        check = gate._check_pdf_exists("/nonexistent")
        assert check.passed is False


# ══════════════════════════════════════════════════════════════════════
# _check_zip_contains_pdf
# ══════════════════════════════════════════════════════════════════════
class TestCheckZipContainsPdf:
    def test_no_zip_fails(self, tmp_path):
        gate = DefenseQualityGate()
        check = gate._check_zip_contains_pdf(str(tmp_path))
        assert check.passed is False

    def test_zip_with_pdf_passes(self, tmp_path):
        zip_path = tmp_path / "交付包.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("报告.pdf", "%PDF fake content")
            zf.writestr("报告.docx", "docx content")
        gate = DefenseQualityGate()
        check = gate._check_zip_contains_pdf(str(tmp_path))
        assert check.passed is True

    def test_zip_without_pdf_fails(self, tmp_path):
        zip_path = tmp_path / "交付包.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("报告.docx", "docx content")
        gate = DefenseQualityGate()
        check = gate._check_zip_contains_pdf(str(tmp_path))
        assert check.passed is False


# ══════════════════════════════════════════════════════════════════════
# _check_forbidden_patterns
# ══════════════════════════════════════════════════════════════════════
class TestCheckForbiddenPatterns:
    def test_no_docx_passes(self, tmp_path):
        gate = DefenseQualityGate()
        checks = gate._check_forbidden_patterns(str(tmp_path))
        assert len(checks) == 1
        assert checks[0].passed is True

    def test_clean_docx_passes(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        render_docx_from_text("答辩状\n正常内容" * 50, str(tmp_path / "答辩状.docx"))
        gate = DefenseQualityGate()
        checks = gate._check_forbidden_patterns(str(tmp_path))
        passed = [c for c in checks if c.passed]
        assert len(passed) > 0

    def test_docx_with_forbidden_fails(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        render_docx_from_text("答辩状\n待补充内容", str(tmp_path / "答辩状.docx"))
        gate = DefenseQualityGate()
        checks = gate._check_forbidden_patterns(str(tmp_path))
        failed = [c for c in checks if not c.passed]
        assert len(failed) >= 1

    def test_docx_with_todo_fails(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        render_docx_from_text("答辩状\nTODO需要修改", str(tmp_path / "答辩状.docx"))
        gate = DefenseQualityGate()
        checks = gate._check_forbidden_patterns(str(tmp_path))
        failed = [c for c in checks if not c.passed]
        assert any("TODO" in c.message for c in failed)

    def test_corrupt_docx_handled(self, tmp_path):
        (tmp_path / "bad.docx").write_bytes(b"not a docx")
        gate = DefenseQualityGate()
        checks = gate._check_forbidden_patterns(str(tmp_path))
        read_check = [c for c in checks if "DOCX读取" in c.check_name]
        assert len(read_check) >= 1


# ══════════════════════════════════════════════════════════════════════
# _check_defense_not_generic
# ══════════════════════════════════════════════════════════════════════
class TestCheckDefenseNotGeneric:
    def test_no_defense_doc_passes(self, tmp_path):
        gate = DefenseQualityGate()
        check = gate._check_defense_not_generic(str(tmp_path))
        assert check.passed is True

    def test_specific_defense_passes(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        render_docx_from_text(
            "民事答辩状\n答辩人：张三\n针对本案具体事实，答辩人认为原告的诉讼请求缺乏事实依据。",
            str(tmp_path / "06_答辩状.docx"),
        )
        gate = DefenseQualityGate()
        check = gate._check_defense_not_generic(str(tmp_path))
        assert check.passed is True

    def test_generic_defense_fails(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        content = (
            "民事答辩状\n"
            "本案基本事实如下：\n"
            "针对原告的诉讼请求，答辩人提出以下答辩意见：\n"
            "根据案件情况，建议采取以下诉讼策略：\n"
            "综合评级：B"
        )
        render_docx_from_text(content, str(tmp_path / "06_答辩状.docx"))
        gate = DefenseQualityGate()
        check = gate._check_defense_not_generic(str(tmp_path))
        assert check.passed is False


# ══════════════════════════════════════════════════════════════════════
# _check_evidence_gap_count
# ══════════════════════════════════════════════════════════════════════
class TestCheckEvidenceGapCount:
    def test_no_distilled_card_fails(self, tmp_path):
        gate = DefenseQualityGate()
        check = gate._check_evidence_gap_count(str(tmp_path))
        assert check.passed is False

    def test_enough_gaps_passes(self, tmp_path):
        internal = tmp_path / "_internal"
        internal.mkdir()
        data = {
            "fact_card": {},
            "strategy_card": {
                "evidence_gap": ["缺口1", "缺口2", "缺口3", "缺口4", "缺口5"],
            },
        }
        (internal / "distilled_card.json").write_text(json.dumps(data), encoding="utf-8")
        gate = DefenseQualityGate()
        check = gate._check_evidence_gap_count(str(tmp_path))
        assert check.passed is True

    def test_too_few_gaps_fails(self, tmp_path):
        internal = tmp_path / "_internal"
        internal.mkdir()
        data = {
            "fact_card": {},
            "strategy_card": {
                "evidence_gap": ["缺口1", "缺口2"],
            },
        }
        (internal / "distilled_card.json").write_text(json.dumps(data), encoding="utf-8")
        gate = DefenseQualityGate()
        check = gate._check_evidence_gap_count(str(tmp_path))
        assert check.passed is False


# ══════════════════════════════════════════════════════════════════════
# _check_action_advice_count
# ══════════════════════════════════════════════════════════════════════
class TestCheckActionAdviceCount:
    def test_no_distilled_card_fails(self, tmp_path):
        gate = DefenseQualityGate()
        check = gate._check_action_advice_count(str(tmp_path))
        assert check.passed is False

    def test_enough_advice_passes(self, tmp_path):
        internal = tmp_path / "_internal"
        internal.mkdir()
        data = {
            "fact_card": {},
            "strategy_card": {
                "action_advice": [
                    {"action": f"建议{i}", "priority": "S", "reasoning": ""}
                    for i in range(6)
                ],
            },
        }
        (internal / "distilled_card.json").write_text(json.dumps(data), encoding="utf-8")
        gate = DefenseQualityGate()
        check = gate._check_action_advice_count(str(tmp_path))
        assert check.passed is True

    def test_too_few_advice_fails(self, tmp_path):
        internal = tmp_path / "_internal"
        internal.mkdir()
        data = {
            "fact_card": {},
            "strategy_card": {
                "action_advice": [{"action": "建议1", "priority": "S", "reasoning": ""}],
            },
        }
        (internal / "distilled_card.json").write_text(json.dumps(data), encoding="utf-8")
        gate = DefenseQualityGate()
        check = gate._check_action_advice_count(str(tmp_path))
        assert check.passed is False


# ══════════════════════════════════════════════════════════════════════
# _check_rating_reasoning
# ══════════════════════════════════════════════════════════════════════
class TestCheckRatingReasoning:
    def test_no_distilled_card_fails(self, tmp_path):
        gate = DefenseQualityGate()
        check = gate._check_rating_reasoning(str(tmp_path))
        assert check.passed is False

    def test_rating_with_reasoning_passes(self, tmp_path):
        internal = tmp_path / "_internal"
        internal.mkdir()
        data = {
            "fact_card": {},
            "strategy_card": {
                "sabcd_rating": "B",
                "situation_assessment": "本案被告面临中等风险，原告提交了部分证据支持其诉讼请求，但被告仍有抗辩空间。" * 3,
            },
        }
        (internal / "distilled_card.json").write_text(json.dumps(data), encoding="utf-8")
        gate = DefenseQualityGate()
        check = gate._check_rating_reasoning(str(tmp_path))
        assert check.passed is True

    def test_no_rating_fails(self, tmp_path):
        internal = tmp_path / "_internal"
        internal.mkdir()
        data = {
            "fact_card": {},
            "strategy_card": {
                "sabcd_rating": "",
                "situation_assessment": "评估内容",
            },
        }
        (internal / "distilled_card.json").write_text(json.dumps(data), encoding="utf-8")
        gate = DefenseQualityGate()
        check = gate._check_rating_reasoning(str(tmp_path))
        assert check.passed is False

    def test_short_reasoning_fails(self, tmp_path):
        internal = tmp_path / "_internal"
        internal.mkdir()
        data = {
            "fact_card": {},
            "strategy_card": {
                "sabcd_rating": "B",
                "situation_assessment": "太短",
            },
        }
        (internal / "distilled_card.json").write_text(json.dumps(data), encoding="utf-8")
        gate = DefenseQualityGate()
        check = gate._check_rating_reasoning(str(tmp_path))
        assert check.passed is False


# ══════════════════════════════════════════════════════════════════════
# run_checks — full integration
# ══════════════════════════════════════════════════════════════════════
class TestRunChecks:
    def test_all_pass(self, tmp_path):
        """Full case with all files should pass all checks."""
        from core.render.docx_renderer import render_docx_from_text
        customer = tmp_path / "customer"
        internal = tmp_path / "_internal"
        customer.mkdir()
        internal.mkdir()

        # Create valid DOCX
        render_docx_from_text("答辩状\n具体案件事实" * 50, str(customer / "06_答辩状.docx"))
        render_docx_from_text("报告\n内容" * 50, str(customer / "01_报告.docx"))

        # Create PDF
        (customer / "01_报告.pdf").write_bytes(b"%PDF-1.4 fake content")

        # Create ZIP with PDF
        with zipfile.ZipFile(str(customer / "交付包.zip"), "w") as zf:
            zf.writestr("01_报告.pdf", "%PDF fake")

        # Create distilled card
        data = {
            "fact_card": {},
            "strategy_card": {
                "sabcd_rating": "B",
                "situation_assessment": "评估内容" * 30,
                "action_advice": [{"action": f"建议{i}", "priority": "S", "reasoning": ""} for i in range(6)],
                "evidence_gap": [f"缺口{i}" for i in range(5)],
            },
        }
        (internal / "distilled_card.json").write_text(json.dumps(data), encoding="utf-8")

        gate = DefenseQualityGate()
        result = gate.run_checks(str(tmp_path), ai_mode="real_ai")
        # Should have many passing checks
        passed = [c for c in result.checks if c.passed]
        assert len(passed) > 0

    def test_local_fallback_blocks(self, tmp_path):
        gate = DefenseQualityGate()
        result = gate.run_checks(str(tmp_path), ai_mode="local_fallback")
        ai_check = [c for c in result.checks if c.check_name == "AI模式验证"]
        assert len(ai_check) == 1
        assert ai_check[0].passed is False
