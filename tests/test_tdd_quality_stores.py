"""TDD tests for core/quality modules and settings/task stores."""
import pytest
import sys, os, json, tempfile
sys.path.insert(0, ".")

from core.fact_card import PipelineContext, FactCard
from core.quality.pipeline_gates import run_step2_gate, run_step3_gate, GateResult


class TestStep2Gate:
    def test_empty_raw_texts(self):
        ctx = PipelineContext()
        ctx.raw_texts = []
        result = run_step2_gate(ctx)
        assert result.status == "blocked"
        assert any(i.rule == "raw_texts_empty" for i in result.issues)

    def test_short_raw_texts(self):
        ctx = PipelineContext()
        ctx.raw_texts = ["短"]
        result = run_step2_gate(ctx)
        assert result.status == "blocked"
        assert any(i.rule == "raw_texts_too_short" for i in result.issues)

    def test_no_fact_card(self):
        ctx = PipelineContext()
        ctx.raw_texts = ["足够长的文本" * 20]
        ctx.fact_card = None
        result = run_step2_gate(ctx)
        assert result.status == "blocked"
        assert any(i.rule == "fact_card_none" for i in result.issues)

    def test_no_key_facts(self):
        ctx = PipelineContext()
        ctx.raw_texts = ["足够长的文本" * 20]
        ctx.fact_card = FactCard(key_facts=[])
        result = run_step2_gate(ctx)
        assert result.status == "warning"

    def test_no_parties_warning(self):
        ctx = PipelineContext()
        ctx.raw_texts = ["足够长的文本" * 20]
        ctx.fact_card = FactCard(key_facts=["事实"], parties=[])
        result = run_step2_gate(ctx)
        assert result.status == "warning"
        assert any(i.rule == "parties_empty" for i in result.issues)

    def test_pass(self):
        ctx = PipelineContext()
        ctx.raw_texts = ["足够长的文本" * 20]
        ctx.fact_card = FactCard(key_facts=["事实"], parties=[])
        # parties empty is warning, not blocking
        result = run_step2_gate(ctx)
        assert result.status in ("passed", "warning")

    def test_full_pass(self):
        from core.fact_card import Party
        ctx = PipelineContext()
        ctx.raw_texts = ["足够长的文本" * 20]
        ctx.fact_card = FactCard(
            key_facts=["事实"],
            parties=[Party(name="A", role="原告")],
        )
        result = run_step2_gate(ctx)
        assert result.status == "passed"


class TestStep3Gate:
    def test_none_fact_card(self):
        ctx = PipelineContext()
        ctx.fact_card = None
        result = run_step3_gate(ctx)
        assert result.status == "blocked"

    def test_no_key_facts_after_enhance(self):
        ctx = PipelineContext()
        ctx.fact_card = FactCard(key_facts=[])
        result = run_step3_gate(ctx)
        assert result.status == "blocked"

    def test_warnings(self):
        ctx = PipelineContext()
        ctx.fact_card = FactCard(
            key_facts=["短"],
            court="",
            parties=[],
            amount="",
        )
        result = run_step3_gate(ctx)
        assert result.status == "warning"  # key_facts too short is warning, not blocked


class TestGateResult:
    def test_empty_result(self):
        r = GateResult()
        assert r.status == "passed"
        assert r.blocking_issues == []
        assert r.warning_issues == []

    def test_to_dict(self):
        from core.quality.pipeline_gates import GateIssue
        r = GateResult(
            status="blocked",
            issues=[GateIssue(rule="r1", severity="blocking", message="m")],
        )
        d = r.to_dict()
        assert d["status"] == "blocked"
        assert len(d["issues"]) == 1


class TestSettingsStore:
    def test_singleton(self):
        from core.settings_store import get_settings_store
        s1 = get_settings_store()
        s2 = get_settings_store()
        assert s1 is s2

    def test_default_settings(self):
        from core.settings_store import SettingsStore
        s = SettingsStore()
        assert s.settings.deepseek.api_key == "" or isinstance(s.settings.deepseek.api_key, str)

    def test_update_deepseek(self):
        from core.settings_store import SettingsStore
        s = SettingsStore()
        s.update_deepseek(api_key="test_key_123")
        assert s.settings.deepseek.api_key == "test_key_123"
        # Reset
        s.update_deepseek(api_key="")

    def test_update_mimo(self):
        from core.settings_store import SettingsStore
        s = SettingsStore()
        s.update_mimo(api_key="mimo_key")
        assert s.settings.mimo.api_key == "mimo_key"
        s.update_mimo(api_key="")

    def test_set_work_mode(self):
        from core.settings_store import SettingsStore
        s = SettingsStore()
        s.set_work_mode("测试模式")
        assert s.settings.work_mode == "测试模式"
        s.set_work_mode("基础预览")

    def test_masked_key(self):
        from core.settings_store import _mask_key
        assert _mask_key("") == ""
        assert _mask_key("short") == "***"
        assert _mask_key("1234567890abcdef") == "123456...cdef"


class TestTaskStore:
    def test_init_db(self):
        from core.task_store import init_db
        init_db()  # should not raise

    def test_create_and_get(self):
        from core.task_store import create_task, get_task
        rec = create_task("被告", "应诉答辩", file_list=["a.pdf"])
        assert rec.task_id.startswith("case_")
        got = get_task(rec.task_id)
        assert got is not None
        assert got.identity == "被告"

    def test_update_status(self):
        from core.task_store import create_task, update_task_status, get_task
        rec = create_task("被告", "应诉答辩")
        update_task_status(rec.task_id, "进行中")
        got = get_task(rec.task_id)
        assert got.status == "进行中"

    def test_complete_task(self):
        from core.task_store import create_task, complete_task, get_task
        rec = create_task("被告", "应诉答辩")
        complete_task(rec.task_id, rating="B", file_count=5)
        got = get_task(rec.task_id)
        assert got.status == "已完成"
        assert got.rating == "B"

    def test_list_recent(self):
        from core.task_store import list_recent
        tasks = list_recent(5)
        assert isinstance(tasks, list)

    def test_list_all(self):
        from core.task_store import list_all
        tasks = list_all()
        assert isinstance(tasks, list)

    def test_count_by_status(self):
        from core.task_store import count_by_status
        counts = count_by_status()
        assert isinstance(counts, dict)


class TestAuditStore:
    def test_init(self):
        from core.audit_store import init_audit_db
        init_audit_db()  # should not raise

    def test_log_and_read(self):
        from core.audit_store import log_event, get_events_for_task
        log_event("test_task_001", "test_event", message="测试事件")
        events = get_events_for_task("test_task_001")
        assert len(events) >= 1
        assert events[-1].event_type == "test_event"

    def test_list_recent(self):
        from core.audit_store import list_recent_events
        events = list_recent_events(10)
        assert isinstance(events, list)

    def test_log_never_raises(self):
        from core.audit_store import log_event
        # Should silently no-op even with bad data
        log_event("", "", message="")
