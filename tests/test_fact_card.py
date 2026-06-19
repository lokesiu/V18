"""Tests for core.fact_card data models."""
import pytest
import sys
sys.path.insert(0, "D:\\codex\\V18")

from core.fact_card import FactCard, StrategyCard, DistilledCard, Party, SourceRef, PipelineContext


def test_fact_card_creation():
    fc = FactCard(case_id="test", court="test court")
    assert fc.case_id == "test"


def test_fact_card_serialization():
    fc = FactCard(case_id="(2024)京01民初123号", parties=[Party(name="张三", role="原告")])
    d = fc.to_dict()
    fc2 = FactCard.from_dict(d)
    assert fc2.case_id == fc.case_id
    assert len(fc2.parties) == 1


def test_strategy_card_serialization():
    sc = StrategyCard(sabcd_rating="B")
    d = sc.to_dict()
    sc2 = StrategyCard.from_dict(d)
    assert sc2.sabcd_rating == "B"


def test_distilled_card_save_load(tmp_path):
    dc = DistilledCard(fact_card=FactCard(case_id="test"))
    path = str(tmp_path / "test.json")
    dc.save(path)
    dc2 = DistilledCard.load(path)
    assert dc2.fact_card.case_id == "test"


def test_pipeline_context_log():
    ctx = PipelineContext()
    ctx.log("test message")
    assert len(ctx.logs) == 1
    assert "test message" in ctx.logs[0]
