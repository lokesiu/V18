"""TDD tests for intake, rendering, and pipeline edge cases."""
import pytest
import sys, os, tempfile
sys.path.insert(0, ".")

from core.fact_card import PipelineContext, FactCard, Party, SourceRef, StrategyCard


class TestIntakeReadFile:
    """Test core.intake.read_file for various formats."""

    def test_read_nonexistent(self):
        from core.intake import read_file
        result = read_file("/nonexistent/file.txt")
        assert "[" in result  # error message

    def test_read_txt_utf8(self, tmp_path):
        from core.intake import read_file
        p = tmp_path / "test.txt"
        p.write_text("测试内容ABC", encoding="utf-8")
        result = read_file(str(p))
        assert "测试内容" in result

    def test_read_empty_txt(self, tmp_path):
        from core.intake import read_file
        p = tmp_path / "empty.txt"
        p.write_text("", encoding="utf-8")
        result = read_file(str(p))
        assert result == ""

    def test_scan_empty_dir(self, tmp_path):
        from core.intake import scan_input_dir
        result = scan_input_dir(str(tmp_path))
        assert result == []

    def test_scan_nonexistent_dir(self):
        from core.intake import scan_input_dir
        result = scan_input_dir("/nonexistent/dir")
        assert result == []

    def test_scan_finds_files(self, tmp_path):
        from core.intake import scan_input_dir
        (tmp_path / "a.txt").write_text("test", encoding="utf-8")
        (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4 fake")
        result = scan_input_dir(str(tmp_path))
        assert len(result) >= 2


class TestRunIntake:
    """Test core.intake.run_intake with PipelineContext."""

    def test_empty_input_dir(self):
        from core.intake import run_intake
        ctx = PipelineContext(input_dir="")
        ctx = run_intake(ctx)
        assert len(ctx.errors) > 0

    def test_nonexistent_dir(self):
        from core.intake import run_intake
        ctx = PipelineContext(input_dir="/nonexistent")
        ctx = run_intake(ctx)
        assert len(ctx.errors) > 0

    def test_valid_dir(self, tmp_path):
        from core.intake import run_intake
        (tmp_path / "test.txt").write_text("测试文本内容" * 20, encoding="utf-8")
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        assert len(ctx.file_list) >= 1
        assert len(ctx.raw_texts) >= 1


class TestDocxRenderer:
    """Test core.render.docx_renderer."""

    def test_render_empty_content(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        out = str(tmp_path / "test.docx")
        result = render_docx_from_text("", out)
        assert result is True
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0

    def test_render_with_title(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        out = str(tmp_path / "test.docx")
        result = render_docx_from_text("正文内容", out, title="标题")
        assert result is True

    def test_render_chinese_content(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        out = str(tmp_path / "test.docx")
        content = "民事答辩状\n\n答辩人：张三\n\n一、答辩请求\n1. 请求驳回"
        result = render_docx_from_text(content, out)
        assert result is True

    def test_render_markdown_content(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        out = str(tmp_path / "test.docx")
        content = "# 标题\n\n## 小节\n\n- 列表项1\n- 列表项2"
        result = render_docx_from_text(content, out)
        assert result is True


class TestXlsxRenderer:
    """Test core.render.xlsx_renderer."""

    def test_render_basic(self, tmp_path):
        from core.render.xlsx_renderer import render_xlsx
        fc = FactCard(case_id="C1")
        out = str(tmp_path / "test.xlsx")
        result = render_xlsx(fc, out)
        assert result is True
        assert os.path.exists(out)

    def test_render_with_refs(self, tmp_path):
        from core.render.xlsx_renderer import render_xlsx
        fc = FactCard(
            case_id="C1",
            source_refs=[SourceRef(file_name="a.pdf", excerpt="证据1")],
        )
        out = str(tmp_path / "test.xlsx")
        result = render_xlsx(fc, out)
        assert result is True


class TestZipBuilder:
    """Test core.render.zip_builder."""

    def test_build_empty_dir(self, tmp_path):
        from core.render.zip_builder import build_zip
        src = tmp_path / "src"
        src.mkdir()
        out = str(tmp_path / "out.zip")
        result = build_zip(str(src), out)
        assert result is True  # creates empty zip

    def test_build_with_files(self, tmp_path):
        from core.render.zip_builder import build_zip
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.docx").write_bytes(b"fake docx")
        (src / "b.pdf").write_bytes(b"%PDF fake")
        out = str(tmp_path / "out.zip")
        result = build_zip(str(src), out)
        assert result is True
        assert os.path.getsize(out) > 0

    def test_nonexistent_dir(self, tmp_path):
        from core.render.zip_builder import build_zip
        out = str(tmp_path / "out.zip")
        result = build_zip("/nonexistent", out)
        assert result is False


class TestPdfConverter:
    """Test core.render.pdf_converter."""

    def test_nonexistent_docx(self, tmp_path):
        from core.render.pdf_converter import convert_to_pdf
        out = str(tmp_path / "out.pdf")
        result = convert_to_pdf("/nonexistent.docx", out)
        assert result is False


class TestPipelineIntegration:
    """Integration tests for pipeline steps."""

    def test_empty_pipeline(self):
        from core.pipeline import run_pipeline
        ctx = PipelineContext(input_dir="", output_dir="")
        ctx = run_pipeline(ctx)
        assert len(ctx.errors) > 0

    def test_pipeline_with_valid_input(self, tmp_path):
        from core.pipeline import run_pipeline
        # Create test input
        (tmp_path / "test.txt").write_text("测试文本内容" * 50, encoding="utf-8")
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(out_dir),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx = run_pipeline(ctx)
        # Should complete without critical errors (non-critical steps may warn)
        assert ctx.fact_card is not None


class TestCheckpointBuilder:
    """Test core.checkpoint_builder."""

    def test_build_snapshot(self):
        from core.checkpoint_builder import build_ctx_snapshot
        ctx = PipelineContext(task_id="T1", identity="被告")
        ctx.fact_card = FactCard(case_id="C1")
        snapshot = build_ctx_snapshot(ctx)
        assert "T1" in snapshot
        assert "C1" in snapshot

    def test_restore_snapshot(self):
        from core.checkpoint_builder import build_ctx_snapshot, restore_ctx_from_snapshot
        ctx = PipelineContext(task_id="T1")
        ctx.fact_card = FactCard(case_id="C1")
        snapshot = build_ctx_snapshot(ctx)

        ctx2 = PipelineContext()
        ctx2 = restore_ctx_from_snapshot(snapshot, ctx2)
        assert ctx2.fact_card is not None
        assert ctx2.fact_card.case_id == "C1"
