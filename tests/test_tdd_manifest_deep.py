"""TDD tests for step7_render_manifest.py — deeper coverage of retry and manifest logic."""
import pytest
import sys, os, json
sys.path.insert(0, ".")

from core.fact_card import (
    PipelineContext, FactCard, Party, DistilledCard, StrategyCard,
)
from core.pipeline.step7_render_manifest import (
    is_retryable, _file_size, _check_source_dependency,
    render_with_manifest, get_manifest_summary, get_manifest_entries,
    retry_render, _build_retry_render_fn,
    _build_docx_retry_fn, _build_pdf_retry_fn,
    _build_xlsx_retry_fn, _build_zip_retry_fn,
    MAX_RETRY,
)


def _make_ts():
    from core.task_store import get_task_store
    return get_task_store()


def _make_audit():
    from core.audit_store import get_audit_store
    return get_audit_store()


# ══════════════════════════════════════════════════════════════════════
# render_with_manifest — deeper branch coverage
# ══════════════════════════════════════════════════════════════════════
class TestRenderWithManifestDeep:
    def test_success_file_exists_skip(self, tmp_path):
        """Already success + file on disk → skip, return True."""
        ctx = PipelineContext()
        ts = _make_ts()
        task_id = "rwm_skip_001"
        out = tmp_path / "a.txt"
        out.write_text("data", encoding="utf-8")
        ts.manifest_init_entry(task_id, "a.txt", "txt")
        ts.manifest_mark_success(task_id, "a.txt", file_size=4)

        called = [False]
        def fn():
            called[0] = True
            return True

        r = render_with_manifest(ctx, task_id, "a.txt", "txt", fn, str(out), ts=ts)
        assert r is True
        assert called[0] is False

    def test_success_but_file_missing_re_renders(self, tmp_path):
        """Success entry but file deleted → re-renders."""
        ctx = PipelineContext()
        ts = _make_ts()
        task_id = "rwm_rerender_001"
        out = tmp_path / "a.txt"
        ts.manifest_init_entry(task_id, "a.txt", "txt")
        ts.manifest_mark_success(task_id, "a.txt", file_size=999)

        def fn():
            out.write_text("re-rendered", encoding="utf-8")
            return True

        r = render_with_manifest(ctx, task_id, "a.txt", "txt", fn, str(out), ts=ts)
        assert r is True
        assert out.read_text(encoding="utf-8") == "re-rendered"

    def test_no_entry_initializes(self, tmp_path):
        """No manifest entry → initializes then renders."""
        ctx = PipelineContext()
        ts = _make_ts()
        task_id = "rwm_init_001"
        out = tmp_path / "new.txt"

        def fn():
            out.write_text("new", encoding="utf-8")
            return True

        r = render_with_manifest(ctx, task_id, "new.txt", "txt", fn, str(out), ts=ts)
        assert r is True
        entry = ts.manifest_get_entry(task_id, "new.txt")
        assert entry is not None
        assert entry["status"] == "success"

    def test_render_fn_returns_false(self, tmp_path):
        ctx = PipelineContext()
        ts = _make_ts()
        task_id = "rwm_fail_001"
        out = tmp_path / "a.txt"

        r = render_with_manifest(ctx, task_id, "a.txt", "txt", lambda: False, str(out), ts=ts)
        assert r is False
        entry = ts.manifest_get_entry(task_id, "a.txt")
        assert entry["status"] == "failed"
        assert entry["error_code"] == "RENDER_FAILED"

    def test_render_fn_raises(self, tmp_path):
        ctx = PipelineContext()
        ts = _make_ts()
        task_id = "rwm_exc_001"
        out = tmp_path / "a.txt"

        def fn():
            raise RuntimeError("boom")

        r = render_with_manifest(ctx, task_id, "a.txt", "txt", fn, str(out), ts=ts)
        assert r is False
        entry = ts.manifest_get_entry(task_id, "a.txt")
        assert entry["status"] == "failed"
        assert entry["error_code"] == "RuntimeError"

    def test_render_success_but_empty_file(self, tmp_path):
        ctx = PipelineContext()
        ts = _make_ts()
        task_id = "rwm_empty_001"
        out = tmp_path / "a.txt"

        def fn():
            out.write_bytes(b"")
            return True

        r = render_with_manifest(ctx, task_id, "a.txt", "txt", fn, str(out), ts=ts)
        assert r is False
        entry = ts.manifest_get_entry(task_id, "a.txt")
        assert entry["error_code"] == "EMPTY_FILE"

    def test_render_with_source_file(self, tmp_path):
        ctx = PipelineContext()
        ts = _make_ts()
        task_id = "rwm_source_001"
        out = tmp_path / "out.pdf"
        src = tmp_path / "source.docx"
        src.write_bytes(b"fake")

        def fn():
            out.write_bytes(b"%PDF fake")
            return True

        r = render_with_manifest(
            ctx, task_id, "out.pdf", "pdf", fn, str(out),
            source_file=str(src), ts=ts,
        )
        assert r is True


# ══════════════════════════════════════════════════════════════════════
# get_manifest_summary / get_manifest_entries
# ══════════════════════════════════════════════════════════════════════
class TestManifestQueryHelpers:
    def test_summary(self, tmp_path):
        ts = _make_ts()
        task_id = "mq_summary_001"
        ts.manifest_init_entry(task_id, "a.docx", "docx")
        ts.manifest_mark_success(task_id, "a.docx", file_size=100)
        ts.manifest_init_entry(task_id, "b.pdf", "pdf")
        ts.manifest_mark_failed(task_id, "b.pdf", error_code="X", error_msg="Y")

        s = get_manifest_summary(task_id, ts=ts)
        assert s.get("success", 0) >= 1
        assert s.get("failed", 0) >= 1

    def test_entries(self, tmp_path):
        ts = _make_ts()
        task_id = "mq_entries_001"
        ts.manifest_init_entry(task_id, "a.docx", "docx")
        ts.manifest_init_entry(task_id, "b.pdf", "pdf")

        entries = get_manifest_entries(task_id, ts=ts)
        names = [e["file_name"] for e in entries]
        assert "a.docx" in names
        assert "b.pdf" in names


# ══════════════════════════════════════════════════════════════════════
# retry_render — comprehensive branch coverage
# ══════════════════════════════════════════════════════════════════════
class TestRetryRender:
    def _create_task(self, ts, identity="被诉方（被告）", goal="应诉答辩"):
        rec = ts.create_task(identity=identity, goal=goal, file_list=[])
        return rec.task_id

    def test_task_not_found(self):
        ts = _make_ts()
        audit = _make_audit()
        r = retry_render("nonexistent_task_xyz", ts=ts, audit=audit)
        assert r == {"error": "task_not_found"}

    def test_no_failed_entries(self, tmp_path):
        ts = _make_ts()
        audit = _make_audit()
        task_id = self._create_task(ts)
        ts.set_task_output(task_id, str(tmp_path))

        r = retry_render(task_id, ts=ts, audit=audit)
        assert r["retried"] == 0
        assert r["succeeded"] == 0

    def test_max_retry_exceeded(self, tmp_path):
        ts = _make_ts()
        audit = _make_audit()
        task_id = self._create_task(ts)
        ts.set_task_output(task_id, str(tmp_path))
        customer = tmp_path / "customer"
        customer.mkdir()

        # Create failed entry with max attempts
        ts.manifest_init_entry(task_id, "a.docx", "docx")
        for _ in range(MAX_RETRY):
            ts.manifest_mark_failed(task_id, "a.docx", error_code="RENDER_FAILED", error_msg="fail")

        r = retry_render(task_id, ts=ts, audit=audit)
        assert r["skipped"] >= 1

    def test_non_retryable_error(self, tmp_path):
        ts = _make_ts()
        audit = _make_audit()
        task_id = self._create_task(ts)
        ts.set_task_output(task_id, str(tmp_path))
        customer = tmp_path / "customer"
        customer.mkdir()

        ts.manifest_init_entry(task_id, "a.docx", "docx")
        ts.manifest_mark_failed(task_id, "a.docx", error_code="FileNotFoundError", error_msg="missing")

        r = retry_render(task_id, ts=ts, audit=audit)
        assert r["skipped"] >= 1

    def test_source_dependency_missing(self, tmp_path):
        ts = _make_ts()
        audit = _make_audit()
        task_id = self._create_task(ts)
        ts.set_task_output(task_id, str(tmp_path))
        customer = tmp_path / "customer"
        customer.mkdir()

        # PDF entry with missing source DOCX
        ts.manifest_init_entry(task_id, "a.pdf", "pdf", source_file=str(tmp_path / "missing.docx"))
        ts.manifest_mark_failed(task_id, "a.pdf", error_code="RENDER_FAILED", error_msg="fail")

        r = retry_render(task_id, ts=ts, audit=audit)
        assert r["skipped"] >= 1

    def test_retry_success(self, tmp_path):
        ts = _make_ts()
        audit = _make_audit()
        task_id = self._create_task(ts)
        ts.set_task_output(task_id, str(tmp_path))
        customer = tmp_path / "customer"
        customer.mkdir()

        # Create a ZIP retry scenario (simplest to test)
        ts.manifest_init_entry(task_id, "交付包.zip", "zip")
        ts.manifest_mark_failed(task_id, "交付包.zip", error_code="RENDER_FAILED", error_msg="fail")

        # Create some files for ZIP
        (customer / "test.txt").write_text("content", encoding="utf-8")

        r = retry_render(task_id, ts=ts, audit=audit, emit_log=lambda m: None)
        # ZIP retry should succeed since build_zip works
        assert r["retried"] >= 1

    def test_retry_fn_none_skips(self, tmp_path):
        """When _build_retry_render_fn returns None, entry is skipped."""
        ts = _make_ts()
        audit = _make_audit()
        task_id = self._create_task(ts)
        ts.set_task_output(task_id, str(tmp_path))
        customer = tmp_path / "customer"
        customer.mkdir()

        # Unknown file type
        ts.manifest_init_entry(task_id, "data.xyz", "xyz")
        ts.manifest_mark_failed(task_id, "data.xyz", error_code="RENDER_FAILED", error_msg="fail")

        r = retry_render(task_id, ts=ts, audit=audit)
        assert r["skipped"] >= 1

    def test_emit_log_callback(self, tmp_path):
        ts = _make_ts()
        audit = _make_audit()
        task_id = self._create_task(ts)
        ts.set_task_output(task_id, str(tmp_path))

        logs = []
        r = retry_render(task_id, ts=ts, audit=audit, emit_log=lambda m: logs.append(m))
        assert len(logs) >= 1  # "没有失败文件需要重试"


# ══════════════════════════════════════════════════════════════════════
# _build_retry_render_fn — branch coverage
# ══════════════════════════════════════════════════════════════════════
class TestBuildRetryRenderFn:
    def test_no_output_dir(self):
        fn = _build_retry_render_fn("a.docx", "docx", "/out", {"output_dir": ""})
        assert fn is None

    def test_docx_type(self, tmp_path):
        task_dict = {
            "output_dir": str(tmp_path),
            "identity": "被诉方（被告）",
            "goal": "应诉答辩",
        }
        fn = _build_retry_render_fn("06_答辩状.docx", "docx", str(tmp_path / "out.docx"), task_dict)
        assert fn is not None
        assert callable(fn)

    def test_pdf_type_no_source(self, tmp_path):
        task_dict = {"output_dir": str(tmp_path)}
        fn = _build_retry_render_fn("a.pdf", "pdf", str(tmp_path / "out.pdf"), task_dict)
        assert fn is None  # source DOCX doesn't exist

    def test_pdf_type_with_source(self, tmp_path):
        customer = tmp_path / "customer"
        customer.mkdir()
        source = customer / "a.docx"
        source.write_bytes(b"fake docx")
        task_dict = {"output_dir": str(tmp_path)}
        fn = _build_retry_render_fn("a.pdf", "pdf", str(customer / "a.pdf"), task_dict)
        assert fn is not None

    def test_xlsx_type(self, tmp_path):
        task_dict = {"output_dir": str(tmp_path)}
        fn = _build_retry_render_fn("证据目录.xlsx", "xlsx", str(tmp_path / "out.xlsx"), task_dict)
        assert fn is not None
        assert callable(fn)

    def test_zip_type(self, tmp_path):
        customer = tmp_path / "customer"
        customer.mkdir()
        task_dict = {"output_dir": str(tmp_path)}
        fn = _build_retry_render_fn("交付包.zip", "zip", str(customer / "交付包.zip"), task_dict)
        assert fn is not None
        assert callable(fn)

    def test_unknown_type(self, tmp_path):
        task_dict = {"output_dir": str(tmp_path)}
        fn = _build_retry_render_fn("data.xyz", "xyz", str(tmp_path / "out.xyz"), task_dict)
        assert fn is None


# ══════════════════════════════════════════════════════════════════════
# _build_docx_retry_fn — branch coverage
# ══════════════════════════════════════════════════════════════════════
class TestBuildDocxRetryFn:
    def test_with_distilled_card(self, tmp_path):
        """DOCX retry with distilled_card available."""
        internal = tmp_path / "_internal"
        internal.mkdir(parents=True)
        dc = DistilledCard(
            fact_card=FactCard(case_id="C1", key_facts=["事实"]),
            strategy_card=StrategyCard(sabcd_rating="B", situation_assessment="评估"),
        )
        dc.save(str(internal / "distilled_card.json"))

        task_dict = {
            "output_dir": str(tmp_path),
            "identity": "被诉方（被告）",
            "goal": "应诉答辩",
        }
        fn = _build_docx_retry_fn("案件处境评估报告.docx", str(tmp_path / "out.docx"), task_dict)
        assert fn is not None
        # Execute it
        result = fn()
        assert result is True

    def test_without_distilled_card(self, tmp_path):
        """DOCX retry without distilled_card → fallback content."""
        task_dict = {
            "output_dir": str(tmp_path),
            "identity": "被诉方（被告）",
            "goal": "应诉答辩",
        }
        fn = _build_docx_retry_fn("答辩状.docx", str(tmp_path / "out.docx"), task_dict)
        assert fn is not None
        result = fn()
        assert result is True

    def test_strategy_doc_type(self, tmp_path):
        """DOCX retry for strategy doc types uses _render_strategy_docx."""
        internal = tmp_path / "_internal"
        internal.mkdir(parents=True)
        dc = DistilledCard(
            fact_card=FactCard(key_facts=["事实"]),
            strategy_card=StrategyCard(
                sabcd_rating="B",
                action_advice=[],
                evidence_gap=["缺口1", "缺口2", "缺口3", "缺口4", "缺口5"],
            ),
        )
        dc.save(str(internal / "distilled_card.json"))

        task_dict = {"output_dir": str(tmp_path), "identity": "被诉方", "goal": "应诉答辩"}
        fn = _build_docx_retry_fn("行动建议书.docx", str(tmp_path / "out.docx"), task_dict)
        assert fn is not None
        result = fn()
        assert result is True


# ══════════════════════════════════════════════════════════════════════
# _build_xlsx_retry_fn — branch coverage
# ══════════════════════════════════════════════════════════════════════
class TestBuildXlsxRetryFn:
    def test_with_distilled_card(self, tmp_path):
        internal = tmp_path / "_internal"
        internal.mkdir(parents=True)
        dc = DistilledCard(fact_card=FactCard(case_id="C1"))
        dc.save(str(internal / "distilled_card.json"))

        task_dict = {"output_dir": str(tmp_path)}
        fn = _build_xlsx_retry_fn("证据目录.xlsx", str(tmp_path / "out.xlsx"), task_dict)
        assert fn is not None
        result = fn()
        assert result is True

    def test_without_distilled_card(self, tmp_path):
        task_dict = {"output_dir": str(tmp_path)}
        fn = _build_xlsx_retry_fn("证据目录.xlsx", str(tmp_path / "out.xlsx"), task_dict)
        assert fn is not None
        result = fn()
        assert result is False  # no data to render


# ══════════════════════════════════════════════════════════════════════
# _build_zip_retry_fn — branch coverage
# ══════════════════════════════════════════════════════════════════════
class TestBuildZipRetryFn:
    def test_zip_retry_success(self, tmp_path):
        customer = tmp_path / "customer"
        customer.mkdir()
        (customer / "a.docx").write_bytes(b"fake")

        fn = _build_zip_retry_fn(str(customer / "交付包.zip"), str(customer))
        assert fn is not None
        result = fn()
        assert result is True

    def test_zip_retry_empty_dir(self, tmp_path):
        customer = tmp_path / "customer"
        customer.mkdir()

        fn = _build_zip_retry_fn(str(customer / "交付包.zip"), str(customer))
        assert fn is not None
        # build_zip creates empty ZIP with README for empty dirs
        result = fn()
        assert result is True


# ══════════════════════════════════════════════════════════════════════
# render_with_manifest — ts=None auto-fetch path
# ══════════════════════════════════════════════════════════════════════
class TestRenderWithManifestAutoFetch:
    def test_auto_fetches_ts(self, tmp_path):
        """When ts=None, should auto-fetch from get_task_store()."""
        ctx = PipelineContext()
        task_id = "rwm_auto_001"
        out = tmp_path / "a.txt"

        # Don't pass ts — let it auto-fetch
        r = render_with_manifest(
            ctx, task_id, "a.txt", "txt",
            lambda: (out.write_text("x", encoding="utf-8"), True)[-1],
            str(out),
        )
        assert r is True
