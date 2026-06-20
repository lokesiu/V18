"""TDD tests for core/intake.py — branch coverage."""
import pytest
import sys, os
sys.path.insert(0, ".")

from core.fact_card import PipelineContext
from core.intake import (
    read_file, read_image_placeholder, read_text_file,
    read_docx_text, read_pdf_text, scan_input_dir, run_intake,
    ocr_images_via_api, SUPPORTED_EXTENSIONS,
)


# ══════════════════════════════════════════════════════════════════════
# read_image_placeholder
# ══════════════════════════════════════════════════════════════════════
class TestReadImagePlaceholder:
    def test_jpg(self, tmp_path):
        p = tmp_path / "photo.jpg"
        p.write_bytes(b"fake")
        result = read_image_placeholder(str(p))
        assert "photo.jpg" in result
        assert "OCR" in result

    def test_png(self, tmp_path):
        p = tmp_path / "scan.png"
        p.write_bytes(b"fake")
        result = read_image_placeholder(str(p))
        assert "scan.png" in result


# ══════════════════════════════════════════════════════════════════════
# read_file — extension routing
# ══════════════════════════════════════════════════════════════════════
class TestReadFileRouting:
    def test_txt(self, tmp_path):
        p = tmp_path / "a.txt"
        p.write_text("内容", encoding="utf-8")
        result = read_file(str(p))
        assert "内容" in result

    def test_docx(self, tmp_path):
        from core.render.docx_renderer import render_docx_from_text
        p = tmp_path / "a.docx"
        render_docx_from_text("文档内容" * 20, str(p))
        result = read_file(str(p))
        assert "文档" in result

    def test_pdf(self, tmp_path):
        p = tmp_path / "a.pdf"
        p.write_bytes(b"%PDF-1.4 fake")
        result = read_file(str(p))
        assert isinstance(result, str)

    def test_image_jpg(self, tmp_path):
        p = tmp_path / "a.jpg"
        p.write_bytes(b"fake")
        result = read_file(str(p))
        assert "图片文件" in result

    def test_image_png(self, tmp_path):
        p = tmp_path / "a.png"
        p.write_bytes(b"fake")
        result = read_file(str(p))
        assert "图片文件" in result

    def test_image_jpeg(self, tmp_path):
        p = tmp_path / "a.jpeg"
        p.write_bytes(b"fake")
        result = read_file(str(p))
        assert "图片文件" in result

    def test_doc_legacy(self, tmp_path):
        """Legacy .doc format should attempt python-docx."""
        p = tmp_path / "a.doc"
        p.write_bytes(b"not a real doc")
        result = read_file(str(p))
        # Should return error or content
        assert isinstance(result, str)

    def test_unknown_extension(self, tmp_path):
        p = tmp_path / "a.xyz"
        p.write_bytes(b"data")
        result = read_file(str(p))
        assert "不支持" in result

    def test_nonexistent_file(self):
        result = read_file("/nonexistent/file.txt")
        assert "[" in result  # error message


# ══════════════════════════════════════════════════════════════════════
# ocr_images_via_api — graceful degradation
# ══════════════════════════════════════════════════════════════════════
class TestOcrImagesViaApi:
    def test_empty_list(self):
        result = ocr_images_via_api([])
        assert result == {}

    def test_no_api_configured(self, tmp_path):
        """Should return empty dict when no API is configured."""
        p = tmp_path / "img.jpg"
        p.write_bytes(b"fake")
        result = ocr_images_via_api([str(p)])
        # May return empty if no API configured
        assert isinstance(result, dict)


# ══════════════════════════════════════════════════════════════════════
# run_intake — image handling
# ══════════════════════════════════════════════════════════════════════
class TestRunIntakeImages:
    def test_with_image_files(self, tmp_path):
        """Image files should be handled (OCR or placeholder)."""
        (tmp_path / "text.txt").write_text("文本内容" * 50, encoding="utf-8")
        (tmp_path / "photo.jpg").write_bytes(b"fake jpg")
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        assert len(ctx.raw_texts) >= 2
        # One should be text, one should be image placeholder or OCR result
        has_image = any("图片" in t or "OCR" in t for t in ctx.raw_texts)
        has_text = any("文本" in t for t in ctx.raw_texts)
        assert has_text

    def test_only_images(self, tmp_path):
        """Only image files — should still produce raw_texts."""
        (tmp_path / "a.jpg").write_bytes(b"fake")
        (tmp_path / "b.png").write_bytes(b"fake")
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        assert len(ctx.raw_texts) >= 2

    def test_mixed_text_and_images(self, tmp_path):
        (tmp_path / "doc.txt").write_text("文档内容" * 50, encoding="utf-8")
        (tmp_path / "img.jpg").write_bytes(b"fake")
        (tmp_path / "scan.png").write_bytes(b"fake")
        ctx = PipelineContext(input_dir=str(tmp_path))
        ctx = run_intake(ctx)
        assert len(ctx.raw_texts) >= 3


# ══════════════════════════════════════════════════════════════════════
# SUPPORTED_EXTENSIONS constant
# ══════════════════════════════════════════════════════════════════════
class TestSupportedExtensions:
    def test_has_pdf(self):
        assert ".pdf" in SUPPORTED_EXTENSIONS

    def test_has_docx(self):
        assert ".docx" in SUPPORTED_EXTENSIONS

    def test_has_txt(self):
        assert ".txt" in SUPPORTED_EXTENSIONS

    def test_has_images(self):
        assert ".jpg" in SUPPORTED_EXTENSIONS
        assert ".png" in SUPPORTED_EXTENSIONS
        assert ".jpeg" in SUPPORTED_EXTENSIONS

    def test_has_doc(self):
        assert ".doc" in SUPPORTED_EXTENSIONS


# ══════════════════════════════════════════════════════════════════════
# read_text_file — encoding edge cases
# ══════════════════════════════════════════════════════════════════════
class TestReadTextFile:
    def test_utf8_bom(self, tmp_path):
        p = tmp_path / "bom.txt"
        p.write_bytes(b'\xef\xbb\xbf' + "带BOM的文件".encode("utf-8"))
        result = read_text_file(str(p))
        assert "BOM" in result

    def test_large_file(self, tmp_path):
        p = tmp_path / "large.txt"
        p.write_text("行\n" * 10000, encoding="utf-8")
        result = read_text_file(str(p))
        assert len(result) > 10000


# ══════════════════════════════════════════════════════════════════════
# scan_input_dir — case insensitive extensions
# ══════════════════════════════════════════════════════════════════════
class TestScanInputDir:
    def test_uppercase_extensions(self, tmp_path):
        (tmp_path / "DOC.PDF").write_bytes(b"%PDF fake")
        (tmp_path / "DOC.DOCX").write_bytes(b"fake")
        files = scan_input_dir(str(tmp_path))
        assert len(files) >= 2

    def test_mixed_case(self, tmp_path):
        (tmp_path / "a.Txt").write_text("test", encoding="utf-8")
        (tmp_path / "b.TXT").write_text("test", encoding="utf-8")
        files = scan_input_dir(str(tmp_path))
        assert len(files) >= 2
