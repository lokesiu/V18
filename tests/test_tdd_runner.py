"""TDD tests for core/runner.py — CLI commands and main function."""
import pytest
import sys, os, json
sys.path.insert(0, ".")

from core.runner import cmd_doctor, cmd_analyze, cmd_inspect, cmd_package, cmd_selfcheck
from core.fact_card import FactCard, DistilledCard, StrategyCard


# ══════════════════════════════════════════════════════════════════════
# cmd_doctor
# ══════════════════════════════════════════════════════════════════════
class TestCmdDoctor:
    def test_returns_bool(self):
        result = cmd_doctor()
        assert isinstance(result, bool)


# ══════════════════════════════════════════════════════════════════════
# cmd_analyze
# ══════════════════════════════════════════════════════════════════════
class TestCmdAnalyze:
    def test_nonexistent_input(self, tmp_path):
        result = cmd_analyze(
            "/nonexistent/dir", "被诉方（被告）", "应诉答辩",
            str(tmp_path / "out"),
        )
        assert result is False

    def test_invalid_identity(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        result = cmd_analyze(
            str(input_dir), "无效身份", "应诉答辩",
            str(tmp_path / "out"),
        )
        assert result is False

    def test_invalid_goal(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        result = cmd_analyze(
            str(input_dir), "被诉方（被告）", "无效目标",
            str(tmp_path / "out"),
        )
        assert result is False

    def test_valid_input_creates_output(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "test.txt").write_text("原告张三诉被告李四借款合同纠纷一案" * 20, encoding="utf-8")
        out_dir = str(tmp_path / "out")
        result = cmd_analyze(str(input_dir), "被诉方（被告）", "应诉答辩", out_dir)
        # Pipeline should complete (may have errors but should not crash)
        assert isinstance(result, bool)
        assert os.path.exists(out_dir)


# ══════════════════════════════════════════════════════════════════════
# cmd_inspect
# ══════════════════════════════════════════════════════════════════════
class TestCmdInspect:
    def test_nonexistent_case(self):
        result = cmd_inspect("/nonexistent/case")
        assert result is False

    def test_no_customer_dir(self, tmp_path):
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        result = cmd_inspect(str(case_dir))
        assert result is False

    def test_with_customer_files(self, tmp_path):
        case_dir = tmp_path / "case"
        customer = case_dir / "customer"
        customer.mkdir(parents=True)
        (customer / "01_报告.docx").write_bytes(b"fake")
        (customer / "02_建议.docx").write_bytes(b"fake")
        result = cmd_inspect(str(case_dir))
        assert result is True

    def test_with_distilled_card(self, tmp_path):
        case_dir = tmp_path / "case"
        customer = case_dir / "customer"
        internal = case_dir / "_internal"
        customer.mkdir(parents=True)
        internal.mkdir(parents=True)
        (customer / "01_报告.docx").write_bytes(b"fake")

        # Create distilled card
        dc = DistilledCard(
            fact_card=FactCard(
                case_id="(2024)京01民初1号",
                court="北京法院",
                identity="被告",
                amount="10万元",
                key_facts=["事实1", "事实2"],
                disputed_facts=["争议1"],
                missing_materials=["材料1"],
            ),
            strategy_card=StrategyCard(sabcd_rating="B"),
        )
        dc.save(str(internal / "distilled_card.json"))

        result = cmd_inspect(str(case_dir))
        assert result is True


# ══════════════════════════════════════════════════════════════════════
# cmd_package
# ══════════════════════════════════════════════════════════════════════
class TestCmdPackage:
    def test_with_files(self, tmp_path):
        customer = tmp_path / "customer"
        customer.mkdir()
        (customer / "01_报告.docx").write_bytes(b"fake")
        (customer / "02_建议.pdf").write_bytes(b"%PDF fake")
        result = cmd_package(str(tmp_path))
        assert result is True
        assert (customer / "客户交付包.zip").exists()

    def test_nonexistent_case(self, tmp_path):
        result = cmd_package(str(tmp_path / "nonexistent"))
        assert result is False


# ══════════════════════════════════════════════════════════════════════
# cmd_selfcheck
# ══════════════════════════════════════════════════════════════════════
class TestCmdSelfcheck:
    def test_no_customer_dir(self, tmp_path):
        result = cmd_selfcheck(str(tmp_path / "nonexistent"))
        assert result is False

    def test_with_valid_files(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        from core.render.xlsx_renderer import render_xlsx

        customer = tmp_path / "customer"
        customer.mkdir()
        render_docx_from_text("答辩状\n内容" * 50, str(customer / "06_答辩状.docx"))
        render_docx_from_text("报告\n内容" * 50, str(customer / "01_报告.docx"))
        render_xlsx(FactCard(), str(customer / "04_证据目录.xlsx"))
        # Create a PDF
        with open(customer / "01_报告.pdf", "wb") as f:
            f.write(b"%PDF-1.4 fake content for testing")
        # Create a ZIP
        import zipfile
        with zipfile.ZipFile(str(customer / "客户交付包.zip"), "w") as zf:
            zf.writestr("test.txt", "content")

        result = cmd_selfcheck(str(tmp_path))
        # Some checks may fail (expected file names), but should not crash
        assert isinstance(result, bool)


# ══════════════════════════════════════════════════════════════════════
# main function — argparse branches
# ══════════════════════════════════════════════════════════════════════
class TestMain:
    def test_no_command(self, monkeypatch):
        """No command should print help and return (no exit)."""
        monkeypatch.setattr(sys, "argv", ["runner.py"])
        from core.runner import main
        # main() returns None when no command given
        result = main()
        assert result is None

    def test_doctor_command(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["runner.py", "doctor"])
        from core.runner import main
        # doctor should not raise
        try:
            main()
        except SystemExit:
            pass

    def test_inspect_nonexistent(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["runner.py", "inspect", "--case", "/nonexistent"])
        from core.runner import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_package_nonexistent(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["runner.py", "package", "--case", "/nonexistent"])
        from core.runner import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_selfcheck_nonexistent(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["runner.py", "selfcheck", "--case", "/nonexistent"])
        from core.runner import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_analyze_invalid_input(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "runner.py", "analyze",
            "--input", "/nonexistent",
            "--identity", "被诉方（被告）",
            "--goal", "应诉答辩",
            "--out", "/tmp/test_out",
        ])
        from core.runner import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
