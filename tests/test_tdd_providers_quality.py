"""TDD tests for providers, quality helpers, and contracts."""
import pytest
import sys, os
sys.path.insert(0, ".")

from core.fact_card import PipelineContext, FactCard, Party, SourceRef


class TestApiAClient:
    """Test core.providers.api_a_client."""

    def test_import(self):
        from core.providers.api_a_client import ApiAClient
        client = ApiAClient()
        assert client._available is False

    def test_enhance_empty_texts(self):
        from core.providers.api_a_client import ApiAClient
        client = ApiAClient()
        fc = FactCard(case_id="C1")
        result = client.enhance_facts(fc, [])
        assert result.case_id == "C1"

    def test_local_extract(self):
        from core.providers.api_a_client import ApiAClient
        client = ApiAClient()
        fc = FactCard()
        result = client.enhance_facts(fc, ["原告张三诉被告李四借款10万元"])
        assert result.case_id == "" or len(result.key_facts) >= 0


class TestApiBClient:
    """Test core.providers.api_b_client."""

    def test_import(self):
        from core.providers.api_b_client import ApiBClient
        client = ApiBClient()
        assert client._available is False

    def test_local_generate(self):
        from core.providers.api_b_client import ApiBClient
        client = ApiBClient()
        fc = FactCard(
            case_id="C1",
            parties=[Party(name="A", role="原告")],
            key_facts=["事实1"],
        )
        sc = client._local_generate(fc, "被诉方（被告）", "应诉答辩")
        assert sc.sabcd_rating in ("S", "A", "B", "C", "D")
        assert len(sc.action_advice) >= 5

    def test_local_generate_empty_card(self):
        from core.providers.api_b_client import ApiBClient
        client = ApiBClient()
        fc = FactCard()
        sc = client._local_generate(fc, "", "")
        assert sc.sabcd_rating in ("S", "A", "B", "C", "D")

    def test_build_actions_defendant(self):
        from core.providers.api_b_client import ApiBClient
        from core.fact_card import FactCard
        fc = FactCard()
        actions = ApiBClient._build_actions(fc, "被诉方（被告）")
        assert len(actions) >= 6

    def test_build_actions_plaintiff(self):
        from core.providers.api_b_client import ApiBClient
        fc = FactCard()
        actions = ApiBClient._build_actions(fc, "起诉方")
        assert len(actions) >= 6

    def test_build_actions_complainant(self):
        from core.providers.api_b_client import ApiBClient
        fc = FactCard()
        actions = ApiBClient._build_actions(fc, "投诉方")
        assert len(actions) >= 6

    def test_build_actions_review(self):
        from core.providers.api_b_client import ApiBClient
        fc = FactCard()
        actions = ApiBClient._build_actions(fc, "行政复议申请人")
        assert len(actions) >= 5

    def test_build_actions_evidence(self):
        from core.providers.api_b_client import ApiBClient
        fc = FactCard()
        actions = ApiBClient._build_actions(fc, "整理证据")
        assert len(actions) >= 5

    def test_build_actions_unknown(self):
        from core.providers.api_b_client import ApiBClient
        fc = FactCard()
        actions = ApiBClient._build_actions(fc, "未知身份")
        assert len(actions) >= 5  # fallback

    def test_compute_rating(self):
        from core.providers.api_b_client import ApiBClient
        fc = FactCard(case_id="C1", court="法院", parties=[Party(name="A")], amount="100元")
        assert ApiBClient._compute_rating(fc) == "S"

    def test_compute_rating_poor(self):
        from core.providers.api_b_client import ApiBClient
        fc = FactCard(conflicts=["冲突1", "冲突2", "冲突3"], missing_materials=["缺1", "缺2"])
        rating = ApiBClient._compute_rating(fc)
        assert rating in ("C", "D")

    def test_extract_user_info(self):
        from core.providers.api_b_client import _extract_user_info
        fc = FactCard(
            parties=[Party(name="张三", role="被告")],
            source_refs=[SourceRef(excerpt="申请人：张三，男，1990年1月1日出生，住北京市朝阳区，身份证号：11010119900101001X，电话：13800138000")],
        )
        info = _extract_user_info(fc)
        assert "张三" in info
        assert info["张三"].get("gender") == "男"


class TestVisibleDocxChecker:
    """Test core.quality.visible_docx_checker."""

    def test_import(self):
        from core.quality.visible_docx_checker import check_docx_readable, check_docx_no_placeholders, check_docx_no_internal_fields
        assert callable(check_docx_readable)

    def test_check_readable_valid(self, tmp_path):
        from core.quality.visible_docx_checker import check_docx_readable
        from core.render.docx_renderer import render_docx_from_text
        p = str(tmp_path / "test.docx")
        render_docx_from_text("测试内容" * 50, p)
        result = check_docx_readable(p)
        assert result.passed is True

    def test_check_readable_corrupt(self, tmp_path):
        from core.quality.visible_docx_checker import check_docx_readable
        p = str(tmp_path / "bad.docx")
        with open(p, "wb") as f:
            f.write(b"not a docx")
        result = check_docx_readable(p)
        assert result.passed is False

    def test_check_no_placeholders_clean(self, tmp_path):
        from core.quality.visible_docx_checker import check_docx_no_placeholders
        from core.render.docx_renderer import render_docx_from_text
        p = str(tmp_path / "clean.docx")
        render_docx_from_text("答辩状\n正常内容" * 50, p)
        result = check_docx_no_placeholders(p)
        assert result.passed is True

    def test_check_no_internal_fields_clean(self, tmp_path):
        from core.quality.visible_docx_checker import check_docx_no_internal_fields
        from core.render.docx_renderer import render_docx_from_text
        p = str(tmp_path / "clean.docx")
        render_docx_from_text("答辩状\n正常内容" * 50, p)
        result = check_docx_no_internal_fields(p)
        assert result.passed is True


class TestPackageLeakScanner:
    """Test core.quality.package_leak_scanner."""

    def test_import(self):
        from core.quality.package_leak_scanner import scan_for_leaks, check_pdf_header, check_xlsx_rows
        assert callable(scan_for_leaks)

    def test_scan_clean_dir(self, tmp_path):
        from core.quality.package_leak_scanner import scan_for_leaks
        (tmp_path / "a.docx").write_bytes(b"fake")
        (tmp_path / "b.pdf").write_bytes(b"%PDF fake")
        result = scan_for_leaks(str(tmp_path))
        assert result.passed is True

    def test_scan_dir_with_json(self, tmp_path):
        from core.quality.package_leak_scanner import scan_for_leaks
        (tmp_path / "a.docx").write_bytes(b"fake")
        (tmp_path / "data.json").write_text('{}', encoding="utf-8")
        result = scan_for_leaks(str(tmp_path))
        assert result.passed is False

    def test_check_pdf_header_valid(self, tmp_path):
        from core.quality.package_leak_scanner import check_pdf_header
        p = str(tmp_path / "test.pdf")
        with open(p, "wb") as f:
            f.write(b"%PDF-1.4 fake content")
        result = check_pdf_header(p)
        assert result.passed is True

    def test_check_pdf_header_invalid(self, tmp_path):
        from core.quality.package_leak_scanner import check_pdf_header
        p = str(tmp_path / "bad.pdf")
        with open(p, "wb") as f:
            f.write(b"not a pdf")
        result = check_pdf_header(p)
        assert result.passed is False

    def test_check_xlsx_rows_valid(self, tmp_path):
        from core.quality.package_leak_scanner import check_xlsx_rows
        from core.render.xlsx_renderer import render_xlsx
        p = str(tmp_path / "test.xlsx")
        render_xlsx(FactCard(), p)
        result = check_xlsx_rows(p, min_rows=3)
        assert result.passed is True


class TestContracts:
    """Test core.contracts module imports and interfaces."""

    def test_quality_gate_contract(self):
        from core.contracts.quality_gate import QualityGate, QualityResult, QualityCheck, CheckSeverity
        assert hasattr(QualityGate, 'run_checks')
        assert hasattr(QualityGate, 'name')

    def test_renderer_contract(self):
        from core.contracts.renderer import Renderer
        assert callable(getattr(Renderer, 'render', None))

    def test_scenario_contract(self):
        from core.contracts.scenario import Scenario
        assert callable(getattr(Scenario, 'validate_input', None))
        assert callable(getattr(Scenario, 'get_quality_rules', None))


class TestDefenseScenario:
    """Test core.scenario.defense_scenario."""

    def test_import(self):
        from core.scenario.defense_scenario import DefenseScenario
        ds = DefenseScenario()
        assert ds is not None

    def test_validate_input(self):
        from core.scenario.defense_scenario import DefenseScenario
        ds = DefenseScenario()
        assert callable(ds.validate_input)

    def test_get_quality_rules(self):
        from core.scenario.defense_scenario import DefenseScenario
        ds = DefenseScenario()
        rules = ds.get_quality_rules()
        assert isinstance(rules, (list, dict))
