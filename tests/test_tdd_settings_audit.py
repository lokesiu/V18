"""TDD tests for settings_store.py and audit_store.py — branch coverage."""
import pytest
import sys, os, json
sys.path.insert(0, ".")

from core.settings_store import (
    SettingsStore, AISettings, DeepSeekSettings, MiMoSettings,
    CustomSettings, _mask_key, get_settings_store,
)
from core.audit_store import (
    log_event, log_task_created, log_task_started,
    log_step_started, log_step_done, log_step_failed,
    log_ai_call, log_quality_blocked, log_quality_resolved,
    log_render_file_done, log_render_file_failed,
    log_task_completed, log_task_failed,
    log_user_retry, log_user_cancel, log_quality_gate,
    log_checkpoint_saved, log_manifest_skipped,
    get_events_for_task, list_recent_events,
    list_events_filtered, count_events_by_type,
    init_audit_db, AuditStore, get_audit_store,
)


# ══════════════════════════════════════════════════════════════════════
# SettingsStore — save/update/to_dict
# ══════════════════════════════════════════════════════════════════════
class TestSettingsStore:
    def test_save_and_reload(self, tmp_path, monkeypatch):
        """Save settings and verify they persist."""
        monkeypatch.setattr("core.settings_store._SETTINGS_DIR", tmp_path)
        monkeypatch.setattr("core.settings_store._SETTINGS_FILE", tmp_path / "settings.json")

        store = SettingsStore()
        store.update_deepseek(api_key="test_key_123", base_url="https://test.api.com")
        store.update_mimo(api_key="mimo_key_456")
        store.set_work_mode("DeepSeek单AI")
        store.save()

        # Verify file exists
        assert (tmp_path / "settings.json").exists()

        # Reload and verify
        store2 = SettingsStore()
        assert store2.settings.deepseek.api_key == "test_key_123"
        assert store2.settings.deepseek.base_url == "https://test.api.com"
        assert store2.settings.mimo.api_key == "mimo_key_456"
        assert store2.settings.work_mode == "DeepSeek单AI"

    def test_update_deepseek_all_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.settings_store._SETTINGS_DIR", tmp_path)
        monkeypatch.setattr("core.settings_store._SETTINGS_FILE", tmp_path / "settings.json")

        store = SettingsStore()
        store.update_deepseek(
            api_key="key",
            base_url="https://url.com",
            model_extract="model-a",
            model_strategy="model-b",
            timeout=30,
        )
        assert store.settings.deepseek.api_key == "key"
        assert store.settings.deepseek.base_url == "https://url.com"
        assert store.settings.deepseek.model_extract == "model-a"
        assert store.settings.deepseek.model_strategy == "model-b"
        assert store.settings.deepseek.timeout == 30

    def test_update_mimo_all_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.settings_store._SETTINGS_DIR", tmp_path)
        monkeypatch.setattr("core.settings_store._SETTINGS_FILE", tmp_path / "settings.json")

        store = SettingsStore()
        store.update_mimo(
            api_key="key",
            base_url="https://url.com",
            model="model-x",
            use_cases=["case1", "case2"],
            timeout=45,
        )
        assert store.settings.mimo.api_key == "key"
        assert store.settings.mimo.model == "model-x"
        assert store.settings.mimo.use_cases == ["case1", "case2"]
        assert store.settings.mimo.timeout == 45

    def test_update_custom(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.settings_store._SETTINGS_DIR", tmp_path)
        monkeypatch.setattr("core.settings_store._SETTINGS_FILE", tmp_path / "settings.json")

        store = SettingsStore()
        store.update_custom(api_key="custom_key", base_url="https://custom.com", model="custom-model")
        assert store.settings.custom.api_key == "custom_key"
        assert store.settings.custom.base_url == "https://custom.com"
        assert store.settings.custom.model == "custom-model"

    def test_update_none_fields_ignored(self, tmp_path, monkeypatch):
        """None values should not overwrite existing settings."""
        monkeypatch.setattr("core.settings_store._SETTINGS_DIR", tmp_path)
        monkeypatch.setattr("core.settings_store._SETTINGS_FILE", tmp_path / "settings.json")

        store = SettingsStore()
        store.update_deepseek(api_key="original")
        store.update_deepseek(base_url="https://new.com")
        assert store.settings.deepseek.api_key == "original"
        assert store.settings.deepseek.base_url == "https://new.com"


class TestAISettings:
    def test_get_ai_mode_both(self):
        s = AISettings()
        s.deepseek.api_key = "ds"
        s.mimo.api_key = "mm"
        assert s.get_ai_mode() == "dual_ai"

    def test_get_ai_mode_ds_only(self):
        s = AISettings()
        s.deepseek.api_key = "ds"
        s.mimo.api_key = ""
        assert s.get_ai_mode() == "deepseek_ai"

    def test_get_ai_mode_mimo_only(self):
        s = AISettings()
        s.deepseek.api_key = ""
        s.mimo.api_key = "mm"
        assert s.get_ai_mode() == "mimo_ai"

    def test_get_ai_mode_neither(self):
        s = AISettings()
        assert s.get_ai_mode() == "local_fallback"

    def test_to_dict(self):
        s = AISettings()
        s.deepseek.api_key = "testkey123456"
        d = s.to_dict()
        assert "work_mode" in d
        assert "deepseek" in d
        assert "mimo" in d
        assert "ai_mode" in d


class TestDeepSeekSettings:
    def test_is_configured(self):
        s = DeepSeekSettings(api_key="key")
        assert s.is_configured() is True

    def test_not_configured(self):
        s = DeepSeekSettings(api_key="")
        assert s.is_configured() is False

    def test_masked_dict(self):
        s = DeepSeekSettings(api_key="abcdefghijklmnop")
        d = s.masked_dict()
        assert "abcdefghijklmnop" not in d["api_key"]
        assert "..." in d["api_key"]


class TestMiMoSettings:
    def test_is_configured(self):
        s = MiMoSettings(api_key="key")
        assert s.is_configured() is True

    def test_not_configured(self):
        s = MiMoSettings(api_key="")
        assert s.is_configured() is False

    def test_masked_dict(self):
        s = MiMoSettings(api_key="abcdefghijklmnop")
        d = s.masked_dict()
        assert "abcdefghijklmnop" not in d["api_key"]
        assert "use_cases" in d


class TestMaskKey:
    def test_empty(self):
        assert _mask_key("") == ""

    def test_short(self):
        assert _mask_key("short") == "***"

    def test_long(self):
        result = _mask_key("abcdefghijklmnop")
        assert result.startswith("abcdef")
        assert result.endswith("mnop")
        assert "..." in result


# ══════════════════════════════════════════════════════════════════════
# AuditStore — convenience writers
# ══════════════════════════════════════════════════════════════════════
class TestAuditConvenienceWriters:
    def test_log_task_created(self):
        log_task_created("test_audit_001", "被告", "应诉答辩", ["a.pdf"])
        events = get_events_for_task("test_audit_001")
        assert any(e.event_type == "task_created" for e in events)

    def test_log_task_started(self):
        log_task_started("test_audit_002")
        events = get_events_for_task("test_audit_002")
        assert any(e.event_type == "task_started" for e in events)

    def test_log_step_started(self):
        log_step_started("test_audit_003", 0, "读取材料")
        events = get_events_for_task("test_audit_003")
        assert any(e.event_type == "step_started" for e in events)

    def test_log_step_done(self):
        log_step_done("test_audit_004", 2, "事实蒸馏", latency_ms=500)
        events = get_events_for_task("test_audit_004")
        assert any(e.event_type == "step_done" for e in events)

    def test_log_step_failed(self):
        log_step_failed("test_audit_005", 3, "策略推演", "timeout")
        events = get_events_for_task("test_audit_005")
        assert any(e.event_type == "step_failed" for e in events)

    def test_log_ai_call_success(self):
        log_ai_call("test_audit_006", "事实蒸馏", "deepseek-chat", 1500,
                     token_usage={"total": 100})
        events = get_events_for_task("test_audit_006")
        assert any(e.event_type == "ai_call" for e in events)

    def test_log_ai_call_error(self):
        log_ai_call("test_audit_007", "策略推演", "mimo", 0,
                     error="timeout")
        events = get_events_for_task("test_audit_007")
        assert any(e.event_type == "ai_call" for e in events)
        assert any(e.severity == "error" for e in events)

    def test_log_quality_blocked(self):
        log_quality_blocked("test_audit_008", 1, [{"rule": "r1", "message": "m"}])
        events = get_events_for_task("test_audit_008")
        assert any(e.event_type == "quality_blocked" for e in events)

    def test_log_quality_resolved(self):
        log_quality_resolved("test_audit_009", 2)
        events = get_events_for_task("test_audit_009")
        assert any(e.event_type == "quality_resolved" for e in events)

    def test_log_render_file_done(self):
        log_render_file_done("test_audit_010", "报告.docx", "docx", 5000)
        events = get_events_for_task("test_audit_010")
        assert any(e.event_type == "render_file_done" for e in events)

    def test_log_render_file_failed(self):
        log_render_file_failed("test_audit_011", "报告.pdf", "pdf", "conversion error")
        events = get_events_for_task("test_audit_011")
        assert any(e.event_type == "render_file_failed" for e in events)

    def test_log_task_completed(self):
        log_task_completed("test_audit_012", "B", 10)
        events = get_events_for_task("test_audit_012")
        assert any(e.event_type == "task_completed" for e in events)

    def test_log_task_failed(self):
        log_task_failed("test_audit_013", "API timeout")
        events = get_events_for_task("test_audit_013")
        assert any(e.event_type == "task_failed" for e in events)

    def test_log_user_retry(self):
        log_user_retry("test_audit_014", 3, 1)
        events = get_events_for_task("test_audit_014")
        assert any(e.event_type == "user_retry" for e in events)

    def test_log_user_cancel(self):
        log_user_cancel("test_audit_015")
        events = get_events_for_task("test_audit_015")
        assert any(e.event_type == "user_cancel" for e in events)

    def test_log_quality_gate_blocked(self):
        log_quality_gate("test_audit_016", "step2", "blocked",
                          [{"severity": "blocking", "message": "问题1"}])
        events = get_events_for_task("test_audit_016")
        assert any("blocked" in e.event_type for e in events)

    def test_log_quality_gate_warning(self):
        log_quality_gate("test_audit_017", "step3", "warning",
                          [{"severity": "warning", "message": "警告1"}])
        events = get_events_for_task("test_audit_017")
        assert any("warning" in e.event_type for e in events)

    def test_log_quality_gate_passed(self):
        log_quality_gate("test_audit_018", "step2", "passed", [])
        events = get_events_for_task("test_audit_018")
        assert any("passed" in e.event_type for e in events)

    def test_log_checkpoint_saved(self):
        log_checkpoint_saved("test_audit_019", 4, "蒸馏合并")
        events = get_events_for_task("test_audit_019")
        assert any(e.event_type == "checkpoint_saved" for e in events)

    def test_log_manifest_skipped(self):
        log_manifest_skipped("test_audit_020", "报告.pdf", "无可用数据")
        events = get_events_for_task("test_audit_020")
        assert any(e.event_type == "manifest_skipped" for e in events)


# ══════════════════════════════════════════════════════════════════════
# AuditStore — read functions
# ══════════════════════════════════════════════════════════════════════
class TestAuditRead:
    def test_list_recent_events(self):
        events = list_recent_events(5)
        assert isinstance(events, list)

    def test_count_events_by_type(self):
        counts = count_events_by_type()
        assert isinstance(counts, dict)

    def test_list_events_filtered_by_severity(self):
        events = list_events_filtered(severity="info", limit=5)
        assert isinstance(events, list)

    def test_list_events_filtered_by_search(self):
        events = list_events_filtered(search="任务", limit=5)
        assert isinstance(events, list)

    def test_list_events_filtered_by_event_type(self):
        events = list_events_filtered(event_type="task_created", limit=5)
        assert isinstance(events, list)

    def test_list_events_filtered_by_task_id(self):
        events = list_events_filtered(task_id="test_audit_001", limit=5)
        assert isinstance(events, list)

    def test_audit_store_singleton(self):
        s1 = get_audit_store()
        s2 = get_audit_store()
        assert s1 is s2

    def test_audit_never_raises(self):
        # Should silently no-op
        log_event("", "", message="")
        log_event("x" * 10000, "y" * 10000, message="z" * 10000)
