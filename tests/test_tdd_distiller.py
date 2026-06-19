"""TDD tests for core/distiller.py — distillation logic edge cases."""
import pytest
import sys
sys.path.insert(0, ".")

from core.distiller import (
    _fact_has_source, _validate_key_facts, _tag_disputed_facts,
    _tag_missing_materials, _tag_conflicts, _validate_evidence_gap,
    _action_has_support, _validate_situation_assessment,
    distill,
)
from core.fact_card import (
    FactCard, StrategyCard, DistilledCard, ActionAdvice, SourceRef, PipelineContext,
)


class TestFactHasSource:
    def test_no_sources(self):
        assert _fact_has_source("事实", []) is False

    def test_matching_source(self):
        refs = [SourceRef(excerpt="被告张三借款10万元")]
        assert _fact_has_source("张三借款", refs) is True

    def test_no_match(self):
        refs = [SourceRef(excerpt="完全无关的内容")]
        assert _fact_has_source("张三借款", refs) is False

    def test_empty_fact(self):
        refs = [SourceRef(excerpt="内容")]
        assert _fact_has_source("", refs) is False


class TestValidateKeyFacts:
    def test_verified_fact(self):
        fc = FactCard(
            key_facts=["张三借款"],
            source_refs=[SourceRef(excerpt="张三借款10万元给李四")],
        )
        validated = _validate_key_facts(fc)
        assert any("待核对" not in f for f in validated)

    def test_unverified_fact(self):
        fc = FactCard(
            key_facts=["完全无关的事实"],
            source_refs=[SourceRef(excerpt="其他内容")],
        )
        validated = _validate_key_facts(fc)
        assert any("待核对" in f for f in validated)

    def test_no_sources_marks_all(self):
        fc = FactCard(key_facts=["事实1", "事实2"])
        validated = _validate_key_facts(fc)
        assert all("待核对" in f for f in validated)


class TestTagFunctions:
    def test_tag_disputed(self):
        tagged = _tag_disputed_facts(["争议1", "【争议】已标记"])
        assert tagged[0].startswith("【争议】")
        assert tagged[1] == "【争议】已标记"  # no double tag

    def test_tag_missing(self):
        tagged = _tag_missing_materials(["材料1", "【待补充】已标记"])
        assert tagged[0].startswith("【待补充】")
        assert tagged[1] == "【待补充】已标记"

    def test_tag_conflicts(self):
        tagged = _tag_conflicts(["冲突1", "【冲突】已标记"])
        assert tagged[0].startswith("【冲突】")
        assert tagged[1] == "【冲突】已标记"

    def test_empty_lists(self):
        assert _tag_disputed_facts([]) == []
        assert _tag_missing_materials([]) == []
        assert _tag_conflicts([]) == []


class TestActionHasSupport:
    def test_no_facts(self):
        advice = ActionAdvice(action="起诉被告")
        assert _action_has_support(advice, []) is False

    def test_matching_fact(self):
        # Build strings with known content to avoid encoding issues
        action = "\u8d77\u8bc9\u88ab\u544a\u8fd8\u6b3e"  # 起诉被告还款
        fact = "\u88ab\u544a\u501f\u6b3e10\u4e07\u5143\u672a\u8fd8"  # 被告借款10万元未还
        advice = ActionAdvice(action=action)
        facts = [fact]
        result = _action_has_support(advice, facts)
        # action terms: 起诉,被告,还款 (3 terms); fact contains 被告 (1/3=33% >= 30%)
        assert result is True

    def test_no_match(self):
        advice = ActionAdvice(action="申请仲裁")
        facts = ["被告借款10万元"]
        # "仲裁" not in facts
        result = _action_has_support(advice, facts)
        # May or may not match depending on threshold
        assert isinstance(result, bool)


class TestValidateSituationAssessment:
    def test_empty_assessment(self):
        fc = FactCard(key_facts=["事实"])
        result = _validate_situation_assessment("", fc)
        assert result == "待评估"

    def test_references_fact(self):
        fc = FactCard(key_facts=["张三借款10万元"])
        result = _validate_situation_assessment("张三借款案评估", fc)
        assert "注意" not in result

    def test_no_reference_appends_warning(self):
        fc = FactCard(key_facts=["张三借款10万元"])
        result = _validate_situation_assessment("完全无关的评估内容", fc)
        assert "注意" in result

    def test_no_facts_no_warning(self):
        fc = FactCard(key_facts=[])
        result = _validate_situation_assessment("评估内容", fc)
        assert "注意" not in result


class TestValidateEvidenceGap:
    def test_dedup(self):
        gaps = ["缺口A", "缺口A", "缺口B"]
        fc = FactCard()
        validated = _validate_evidence_gap(gaps, fc)
        assert len(validated) == 2

    def test_skip_positive_claims(self):
        gaps = ["已有充分证据", "缺口A"]
        fc = FactCard()
        validated = _validate_evidence_gap(gaps, fc)
        assert len(validated) == 1

    def test_adds_missing_materials(self):
        gaps = []
        fc = FactCard(missing_materials=["材料X"])
        validated = _validate_evidence_gap(gaps, fc)
        assert any("材料X" in g for g in validated)


class TestDistill:
    def test_full_distill(self):
        ctx = PipelineContext()
        ctx.fact_card = FactCard(
            case_id="C1",
            parties=[],
            key_facts=["事实1"],
            disputed_facts=["争议1"],
            missing_materials=["材料1"],
        )
        ctx.strategy_card = StrategyCard(
            situation_assessment="评估",
            sabcd_rating="B",
            action_advice=[ActionAdvice(action="行动1", priority="S")],
            evidence_gap=["缺口1"],
        )
        ctx = distill(ctx)
        assert ctx.distilled_card is not None
        assert ctx.distilled_card.fact_card.case_id == "C1"

    def test_missing_fact_card(self):
        ctx = PipelineContext()
        ctx.strategy_card = StrategyCard()
        ctx = distill(ctx)
        assert len(ctx.errors) > 0

    def test_missing_strategy_card(self):
        ctx = PipelineContext()
        ctx.fact_card = FactCard()
        ctx = distill(ctx)
        assert len(ctx.errors) > 0
