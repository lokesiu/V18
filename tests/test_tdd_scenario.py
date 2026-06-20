"""TDD tests for scenario registry and defense scenario."""
import pytest
import sys
sys.path.insert(0, ".")

from core.fact_card import PipelineContext
from core.contracts.scenario import ScenarioConfig, ScenarioStatus
from core.scenario.defense_scenario import DefenseScenario
from core.scenario.scenario_registry import ScenarioRegistry, get_scenario_registry


# ══════════════════════════════════════════════════════════════════════
# DefenseScenario
# ══════════════════════════════════════════════════════════════════════
class TestDefenseScenario:
    def test_config(self):
        ds = DefenseScenario()
        cfg = ds.config
        assert cfg.identity == "被诉方"
        assert cfg.goal == "应诉答辩"
        assert cfg.status == ScenarioStatus.ACTIVE
        assert cfg.is_available() is True

    def test_config_has_quality_rules(self):
        ds = DefenseScenario()
        cfg = ds.config
        assert len(cfg.quality_rules) > 0
        assert cfg.min_action_advice == 6
        assert cfg.min_evidence_gap == 5

    def test_config_has_required_docs(self):
        ds = DefenseScenario()
        cfg = ds.config
        assert "答辩状" in cfg.required_doc_types

    def test_config_to_dict(self):
        ds = DefenseScenario()
        d = ds.config.to_dict()
        assert d["identity"] == "被诉方"
        assert d["is_available"] is True

    def test_validate_valid_input(self):
        ds = DefenseScenario()
        ctx = PipelineContext(
            identity="被诉方",
            goal="应诉答辩",
            input_dir="/some/dir",
        )
        errors = ds.validate_input(ctx)
        assert errors == []

    def test_validate_empty_identity(self):
        ds = DefenseScenario()
        ctx = PipelineContext(identity="", goal="应诉答辩", input_dir="/dir")
        errors = ds.validate_input(ctx)
        assert any("身份未设置" in e for e in errors)

    def test_validate_wrong_identity(self):
        ds = DefenseScenario()
        ctx = PipelineContext(identity="起诉方", goal="应诉答辩", input_dir="/dir")
        errors = ds.validate_input(ctx)
        assert any("身份不匹配" in e for e in errors)

    def test_validate_empty_goal(self):
        ds = DefenseScenario()
        ctx = PipelineContext(identity="被诉方", goal="", input_dir="/dir")
        errors = ds.validate_input(ctx)
        assert any("目标未设置" in e for e in errors)

    def test_validate_wrong_goal(self):
        ds = DefenseScenario()
        ctx = PipelineContext(identity="被诉方", goal="起诉立案", input_dir="/dir")
        errors = ds.validate_input(ctx)
        assert any("目标不匹配" in e for e in errors)

    def test_validate_no_input_dir(self):
        ds = DefenseScenario()
        ctx = PipelineContext(identity="被诉方", goal="应诉答辩", input_dir="")
        errors = ds.validate_input(ctx)
        assert any("输入目录未设置" in e for e in errors)

    def test_get_quality_rules(self):
        ds = DefenseScenario()
        rules = ds.get_quality_rules()
        assert rules["min_action_advice"] == 6
        assert rules["min_evidence_gap"] == 5
        assert rules["require_sabcd_rating"] is True
        assert rules["require_pdf"] is True
        assert rules["require_zip"] is True
        assert len(rules["forbidden_patterns"]) > 0

    def test_get_coming_soon_message(self):
        ds = DefenseScenario()
        msg = ds.get_coming_soon_message()
        assert len(msg) > 0


# ══════════════════════════════════════════════════════════════════════
# ScenarioConfig
# ══════════════════════════════════════════════════════════════════════
class TestScenarioConfig:
    def test_active_is_available(self):
        cfg = ScenarioConfig(
            identity="被诉方", goal="应诉答辩",
            display_name="test", description="test",
            status=ScenarioStatus.ACTIVE,
        )
        assert cfg.is_available() is True

    def test_beta_is_available(self):
        cfg = ScenarioConfig(
            identity="x", goal="y",
            display_name="t", description="t",
            status=ScenarioStatus.BETA,
        )
        assert cfg.is_available() is True

    def test_coming_soon_not_available(self):
        cfg = ScenarioConfig(
            identity="x", goal="y",
            display_name="t", description="t",
            status=ScenarioStatus.COMING_SOON,
        )
        assert cfg.is_available() is False

    def test_disabled_not_available(self):
        cfg = ScenarioConfig(
            identity="x", goal="y",
            display_name="t", description="t",
            status=ScenarioStatus.DISABLED,
        )
        assert cfg.is_available() is False

    def test_to_dict(self):
        cfg = ScenarioConfig(
            identity="被诉方", goal="应诉答辩",
            display_name="test", description="desc",
        )
        d = cfg.to_dict()
        assert d["identity"] == "被诉方"
        assert d["is_available"] is True
        assert "status" in d


# ══════════════════════════════════════════════════════════════════════
# ScenarioRegistry
# ══════════════════════════════════════════════════════════════════════
class TestScenarioRegistry:
    def test_register_and_get(self):
        reg = ScenarioRegistry()
        ds = DefenseScenario()
        reg.register(ds)
        found = reg.get("被诉方", "应诉答辩")
        assert found is not None
        assert found.config.identity == "被诉方"

    def test_get_not_found(self):
        reg = ScenarioRegistry()
        assert reg.get("不存在", "不存在") is None

    def test_get_all(self):
        reg = ScenarioRegistry()
        all_scenarios = reg.get_all()
        assert len(all_scenarios) >= 1  # at least defense

    def test_get_active(self):
        reg = ScenarioRegistry()
        active = reg.get_active()
        assert len(active) >= 1
        for s in active:
            assert s.config.status == ScenarioStatus.ACTIVE

    def test_get_coming_soon(self):
        reg = ScenarioRegistry()
        coming = reg.get_coming_soon()
        assert len(coming) >= 1
        for s in coming:
            assert s.config.status == ScenarioStatus.COMING_SOON

    def test_is_available_defense(self):
        reg = ScenarioRegistry()
        assert reg.is_available("被诉方", "应诉答辩") is True

    def test_is_available_coming_soon(self):
        reg = ScenarioRegistry()
        assert reg.is_available("投诉方", "投诉举报") is False

    def test_is_available_not_found(self):
        reg = ScenarioRegistry()
        assert reg.is_available("不存在", "不存在") is False

    def test_defaults_registered(self):
        reg = ScenarioRegistry()
        # Defense should be registered
        assert reg.get("被诉方", "应诉答辩") is not None
        # Coming soon should be registered
        assert reg.get("投诉方", "投诉举报") is not None
        assert reg.get("起诉方", "起诉立案") is not None
        assert reg.get("行政复议申请人", "行政复议") is not None
        assert reg.get("整理证据", "证据整理") is not None

    def test_coming_soon_validate_input(self):
        reg = ScenarioRegistry()
        s = reg.get("投诉方", "投诉举报")
        assert s is not None
        ctx = PipelineContext(identity="投诉方", goal="投诉举报")
        errors = s.validate_input(ctx)
        assert len(errors) > 0
        assert "暂未开放" in errors[0]

    def test_coming_soon_get_quality_rules(self):
        reg = ScenarioRegistry()
        s = reg.get("投诉方", "投诉举报")
        assert s is not None
        rules = s.get_quality_rules()
        assert rules == {}

    def test_coming_soon_config(self):
        reg = ScenarioRegistry()
        s = reg.get("投诉方", "投诉举报")
        assert s is not None
        cfg = s.config
        assert cfg.identity == "投诉方"
        assert cfg.goal == "投诉举报"
        assert cfg.status == ScenarioStatus.COMING_SOON
        assert cfg.is_available() is False

    def test_singleton(self):
        r1 = get_scenario_registry()
        r2 = get_scenario_registry()
        assert r1 is r2

    def test_register_custom_scenario(self):
        reg = ScenarioRegistry()
        from core.contracts.scenario import Scenario as ScenarioABC

        class CustomScenario(ScenarioABC):
            @property
            def config(self):
                return ScenarioConfig(
                    identity="自定义", goal="测试",
                    display_name="自定义测试", description="test",
                )
            def validate_input(self, ctx):
                return []
            def get_quality_rules(self):
                return {}

        reg.register(CustomScenario())
        assert reg.get("自定义", "测试") is not None
        assert reg.is_available("自定义", "测试") is True
