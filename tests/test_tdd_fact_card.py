"""TDD tests for core/fact_card.py — data model edge cases."""
import pytest
import sys, os, json, tempfile
sys.path.insert(0, ".")

from core.fact_card import (
    Party, SourceRef, FactCard, ActionAdvice, DraftDocument,
    StrategyCard, DistilledCard, PipelineContext,
)


class TestParty:
    def test_empty_party(self):
        p = Party()
        assert p.name == ""
        assert p.role == ""

    def test_roundtrip(self):
        p = Party(name="张三", role="原告")
        d = p.to_dict()
        p2 = Party.from_dict(d)
        assert p2.name == "张三"
        assert p2.role == "原告"

    def test_from_dict_missing_keys(self):
        p = Party.from_dict({})
        assert p.name == ""
        assert p.role == ""

    def test_from_dict_extra_keys(self):
        p = Party.from_dict({"name": "X", "role": "Y", "extra": 123})
        assert p.name == "X"


class TestSourceRef:
    def test_roundtrip(self):
        s = SourceRef(file_name="a.pdf", page=3, excerpt="hello")
        d = s.to_dict()
        s2 = SourceRef.from_dict(d)
        assert s2.file_name == "a.pdf"
        assert s2.page == 3
        assert s2.excerpt == "hello"

    def test_none_page(self):
        s = SourceRef(page=None)
        d = s.to_dict()
        assert d["page"] is None
        s2 = SourceRef.from_dict(d)
        assert s2.page is None


class TestFactCard:
    def test_empty_card(self):
        fc = FactCard()
        assert fc.case_id == ""
        assert fc.parties == []
        assert fc.key_facts == []

    def test_roundtrip(self):
        fc = FactCard(
            case_id="(2024)京01民初1号",
            court="北京法院",
            parties=[Party(name="A", role="原告")],
            key_facts=["事实1"],
        )
        d = fc.to_dict()
        fc2 = FactCard.from_dict(d)
        assert fc2.case_id == "(2024)京01民初1号"
        assert len(fc2.parties) == 1
        assert fc2.parties[0].name == "A"

    def test_from_dict_empty(self):
        fc = FactCard.from_dict({})
        assert fc.case_id == ""
        assert fc.parties == []

    def test_list_independence(self):
        """Modifying original list should not affect the card."""
        fc = FactCard()
        fc.key_facts.append("X")
        fc2 = FactCard.from_dict(fc.to_dict())
        fc.key_facts.append("Y")
        assert len(fc2.key_facts) == 1


class TestStrategyCard:
    def test_roundtrip(self):
        sc = StrategyCard(
            sabcd_rating="B",
            situation_assessment="评估",
            action_advice=[ActionAdvice(action="做X", priority="S")],
            evidence_gap=["缺口1"],
            risk_warnings=["风险1"],
        )
        d = sc.to_dict()
        sc2 = StrategyCard.from_dict(d)
        assert sc2.sabcd_rating == "B"
        assert len(sc2.action_advice) == 1
        assert sc2.action_advice[0].priority == "S"

    def test_empty(self):
        sc = StrategyCard.from_dict({})
        assert sc.sabcd_rating == ""
        assert sc.action_advice == []


class TestDistilledCard:
    def test_save_load(self, tmp_path):
        dc = DistilledCard(
            fact_card=FactCard(case_id="C1"),
            strategy_card=StrategyCard(sabcd_rating="A"),
        )
        path = str(tmp_path / "test.json")
        dc.save(path)
        dc2 = DistilledCard.load(path)
        assert dc2.fact_card.case_id == "C1"
        assert dc2.strategy_card.sabcd_rating == "A"

    def test_save_has_meta(self, tmp_path):
        dc = DistilledCard()
        path = str(tmp_path / "test.json")
        dc.save(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "_meta" in data
        assert data["_meta"]["version"] == "V18"


class TestPipelineContext:
    def test_log(self):
        ctx = PipelineContext()
        ctx.log("test message")
        assert len(ctx.logs) == 1
        assert "test message" in ctx.logs[0]

    def test_add_error(self):
        ctx = PipelineContext()
        ctx.add_error("bad")
        assert len(ctx.errors) == 1
        assert "bad" in ctx.errors[0]
        # add_error also logs
        assert len(ctx.logs) == 1

    def test_roundtrip(self):
        ctx = PipelineContext(
            input_dir="/in",
            output_dir="/out",
            identity="被告",
            goal="应诉答辩",
        )
        ctx.fact_card = FactCard(case_id="C1")
        ctx.strategy_card = StrategyCard(sabcd_rating="B")
        d = ctx.to_dict()
        ctx2 = PipelineContext.from_dict(d)
        assert ctx2.input_dir == "/in"
        assert ctx2.identity == "被告"
        assert ctx2.fact_card.case_id == "C1"

    def test_from_dict_none_cards(self):
        d = {"input_dir": "x", "fact_card": None, "strategy_card": None}
        ctx = PipelineContext.from_dict(d)
        assert ctx.fact_card is None
        assert ctx.strategy_card is None
