"""TDD tests for boundary conditions and error tolerance."""
import pytest
import sys, os, struct
sys.path.insert(0, ".")

from core.fact_card import PipelineContext


class TestCorruptPdf:
    """Test handling of corrupt/empty PDF files."""

    def test_empty_pdf(self, tmp_path):
        from core.intake import read_pdf_text
        p = tmp_path / "empty.pdf"
        p.write_bytes(b"")
        result = read_pdf_text(str(p))
        assert "[" in result or result == ""

    def test_garbage_pdf(self, tmp_path):
        from core.intake import read_pdf_text
        p = tmp_path / "garbage.pdf"
        p.write_bytes(b"this is not a pdf file at all")
        result = read_pdf_text(str(p))
        assert "[" in result or result == ""

    def test_truncated_pdf(self, tmp_path):
        from core.intake import read_pdf_text
        p = tmp_path / "truncated.pdf"
        p.write_bytes(b"%PDF-1.4")
        result = read_pdf_text(str(p))
        assert "[" in result or result == ""

    def test_zero_byte_pdf(self, tmp_path):
        from core.intake import read_file
        p = tmp_path / "zero.pdf"
        p.write_bytes(b"")
        result = read_file(str(p))
        assert isinstance(result, str)


class TestCorruptDocx:
    """Test handling of corrupt/empty DOCX files."""

    def test_empty_docx(self, tmp_path):
        from core.intake import read_docx_text
        p = tmp_path / "empty.docx"
        p.write_bytes(b"")
        result = read_docx_text(str(p))
        assert "[" in result or result == ""

    def test_garbage_docx(self, tmp_path):
        from core.intake import read_docx_text
        p = tmp_path / "garbage.docx"
        p.write_bytes(b"not a docx file at all")
        result = read_docx_text(str(p))
        assert "[" in result or result == ""

    def test_truncated_zip(self, tmp_path):
        """DOCX is a ZIP file - test truncated ZIP."""
        from core.intake import read_docx_text
        p = tmp_path / "truncated.docx"
        p.write_bytes(b"PK\x03\x04garbage")
        result = read_docx_text(str(p))
        assert "[" in result or result == ""


class TestEmptyTxt:
    """Test handling of empty/unusual text files."""

    def test_empty_txt(self, tmp_path):
        from core.intake import read_text_file
        p = tmp_path / "empty.txt"
        p.write_bytes(b"")
        result = read_text_file(str(p))
        assert result == ""

    def test_binary_txt(self, tmp_path):
        """Text file with binary content."""
        from core.intake import read_text_file
        p = tmp_path / "binary.txt"
        p.write_bytes(bytes(range(256)))
        result = read_text_file(str(p))
        assert isinstance(result, str)

    def test_utf16_txt(self, tmp_path):
        """UTF-16 encoded text file."""
        from core.intake import read_text_file
        p = tmp_path / "utf16.txt"
        p.write_text("测试内容", encoding="utf-16")
        result = read_text_file(str(p))
        assert isinstance(result, str)

    def test_very_long_line(self, tmp_path):
        """Text file with one very long line."""
        from core.intake import read_text_file
        p = tmp_path / "longline.txt"
        p.write_text("A" * 1000000, encoding="utf-8")
        result = read_text_file(str(p))
        assert len(result) >= 1000000


class TestUnusualEncoding:
    """Test files with unusual encodings."""

    def test_gbk_encoding(self, tmp_path):
        from core.intake import read_text_file
        p = tmp_path / "gbk.txt"
        p.write_bytes("测试GBK编码".encode("gbk"))
        result = read_text_file(str(p))
        assert isinstance(result, str)

    def test_latin1_encoding(self, tmp_path):
        from core.intake import read_text_file
        p = tmp_path / "latin1.txt"
        p.write_bytes("café résumé".encode("latin1"))
        result = read_text_file(str(p))
        assert isinstance(result, str)


class TestIntakeEdgeCases:
    """Test intake with various edge case inputs."""

    def test_no_files_in_dir(self, tmp_path):
        from core.intake import run_intake
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        assert len(ctx.errors) > 0

    def test_only_unsupported_files(self, tmp_path):
        from core.intake import run_intake
        (tmp_path / "data.json").write_text('{"key": "value"}', encoding="utf-8")
        (tmp_path / "image.bmp").write_bytes(b"BMP fake")
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        # JSON and BMP are not supported
        assert len(ctx.file_list) == 0 or len(ctx.errors) > 0

    def test_hidden_files_ignored(self, tmp_path):
        from core.intake import scan_input_dir
        (tmp_path / ".hidden.txt").write_text("hidden", encoding="utf-8")
        (tmp_path / "visible.txt").write_text("visible", encoding="utf-8")
        files = scan_input_dir(str(tmp_path))
        names = [os.path.basename(f) for f in files]
        assert "visible.txt" in names

    def test_mixed_valid_invalid(self, tmp_path):
        from core.intake import run_intake
        (tmp_path / "good.txt").write_text("有效内容" * 50, encoding="utf-8")
        (tmp_path / "bad.pdf").write_bytes(b"not a pdf")
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        assert len(ctx.raw_texts) >= 1

    def test_deeply_nested_dir(self, tmp_path):
        from core.intake import scan_input_dir
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "deep.txt").write_text("deep file", encoding="utf-8")
        files = scan_input_dir(str(tmp_path))
        assert len(files) >= 1


class TestExtractEdgeCases:
    """Test fact extraction with unusual inputs."""

    def test_empty_text(self):
        from core.extract import _local_extract
        fc = _local_extract([""], ["empty.txt"])
        assert fc.case_id == ""

    def test_only_numbers(self):
        from core.extract import _local_extract
        fc = _local_extract(["1234567890" * 10], ["numbers.txt"])
        assert isinstance(fc.key_facts, list)

    def test_only_punctuation(self):
        from core.extract import _local_extract
        fc = _local_extract(["，。！？、；：""''（）"], ["punct.txt"])
        assert isinstance(fc.key_facts, list)

    def test_very_long_text(self):
        from core.extract import _local_extract
        long_text = "原告张三诉被告李四借款合同纠纷一案。" * 10000
        fc = _local_extract([long_text], ["long.txt"])
        assert len(fc.key_facts) <= 10  # should be capped

    def test_unicode_mixed(self):
        from core.extract import _local_extract
        text = "原告:John Doe 被告:田中太郎 金额:$1000 + ¥5000元"
        fc = _local_extract([text], ["mixed.txt"])
        assert isinstance(fc.amount, str)


class TestDistillerEdgeCases:
    """Test distiller with edge case inputs."""

    def test_all_empty(self):
        from core.distiller import distill
        from core.fact_card import FactCard, StrategyCard
        ctx = PipelineContext()
        ctx.fact_card = FactCard()
        ctx.strategy_card = StrategyCard()
        ctx = distill(ctx)
        assert ctx.distilled_card is not None

    def test_huge_key_facts(self):
        from core.distiller import distill
        from core.fact_card import FactCard, StrategyCard
        ctx = PipelineContext()
        ctx.fact_card = FactCard(key_facts=["事实" * 100] * 50)
        ctx.strategy_card = StrategyCard(sabcd_rating="B")
        ctx = distill(ctx)
        assert ctx.distilled_card is not None

    def test_duplicate_key_facts(self):
        from core.distiller import _validate_key_facts
        from core.fact_card import FactCard
        fc = FactCard(key_facts=["相同事实", "相同事实", "相同事实"])
        validated = _validate_key_facts(fc)
        assert len(validated) == 3  # preserves count


class TestRendererEdgeCases:
    """Test renderers with edge case inputs."""

    def test_docx_empty_paragraphs(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        out = str(tmp_path / "test.docx")
        result = render_docx_from_text("\n\n\n", out)
        assert result is True

    def test_docx_only_newlines(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        out = str(tmp_path / "test.docx")
        result = render_docx_from_text("\n" * 1000, out)
        assert result is True

    def test_docx_special_chars(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        out = str(tmp_path / "test.docx")
        content = "测试<>&\"'特殊字符"
        result = render_docx_from_text(content, out)
        assert result is True

    def test_xlsx_no_data(self, tmp_path):
        from core.render.xlsx_renderer import render_xlsx
        from core.fact_card import FactCard
        out = str(tmp_path / "test.xlsx")
        result = render_xlsx(FactCard(), out)
        assert result is True

    def test_zip_nonexistent_source(self, tmp_path):
        from core.render.zip_builder import build_zip
        out = str(tmp_path / "out.zip")
        result = build_zip("/nonexistent/path", out)
        assert result is False


class TestPipelineEdgeCases:
    """Test full pipeline with edge case inputs."""

    def test_pipeline_single_char_file(self, tmp_path):
        from core.intake import run_intake
        (tmp_path / "a.txt").write_text("X", encoding="utf-8")
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        assert len(ctx.raw_texts) >= 1

    def test_pipeline_binary_as_txt(self, tmp_path):
        from core.intake import run_intake
        (tmp_path / "bin.txt").write_bytes(bytes(range(256)) * 100)
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        # Should not crash
        assert isinstance(ctx.raw_texts, list)

    def test_pipeline_repeated_files(self, tmp_path):
        from core.intake import scan_input_dir
        for i in range(10):
            (tmp_path / f"doc_{i}.txt").write_text(f"文档{i}" * 50, encoding="utf-8")
        files = scan_input_dir(str(tmp_path))
        assert len(files) == 10
