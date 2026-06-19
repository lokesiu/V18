"""TDD tests for core/extract.py — regex extraction edge cases."""
import pytest
import sys
sys.path.insert(0, ".")

from core.extract import (
    _extract_case_ids, _extract_court, _extract_parties,
    _extract_amounts, _extract_dates, _extract_deadline,
    _extract_key_facts, _extract_disputed_facts,
)


class TestCaseIdExtraction:
    def test_standard_format(self):
        text = "案号：(2024)京01民初123号"
        ids = _extract_case_ids(text)
        assert len(ids) >= 1
        assert "2024" in ids[0]

    def test_chinese_parens(self):
        text = "（2023）粤03民终456号"
        ids = _extract_case_ids(text)
        assert len(ids) >= 1

    def test_no_match(self):
        ids = _extract_case_ids("没有案号的文本")
        assert ids == []

    def test_multiple_cases(self):
        text = "(2024)京01民初1号 (2023)沪02民终2号"
        ids = _extract_case_ids(text)
        assert len(ids) >= 2


class TestCourtExtraction:
    def test_basic_court(self):
        text = "广东省廉江市人民法院"
        court = _extract_court(text)
        assert "人民法院" in court

    def test_arbitration(self):
        text = "提交北京仲裁委员会仲裁"
        court = _extract_court(text)
        assert "仲裁委员会" in court

    def test_no_court(self):
        court = _extract_court("没有法院的文本")
        assert court == ""


class TestPartyExtraction:
    def test_plaintiff_defendant(self):
        text = "原告：张三\n被告：李四"
        parties = _extract_parties(text)
        names = [p.name for p in parties]
        assert "张三" in names
        assert "李四" in names

    def test_no_parties(self):
        parties = _extract_parties("没有当事人文本")
        assert parties == []

    def test_dedup(self):
        text = "原告：张三\n原告：张三"
        parties = _extract_parties(text)
        count = sum(1 for p in parties if p.name == "张三")
        assert count == 1


class TestAmountExtraction:
    def test_yuan(self):
        amounts = _extract_amounts("赔偿人民币10000元")
        assert len(amounts) >= 1

    def test_wanyuan(self):
        amounts = _extract_amounts("支付5万元")
        assert len(amounts) >= 1

    def test_no_amount(self):
        amounts = _extract_amounts("没有金额")
        assert amounts == []


class TestDateExtraction:
    def test_chinese_date(self):
        dates = _extract_dates("2024年6月15日签订合同")
        assert len(dates) >= 1
        assert "2024" in dates[0]

    def test_no_date(self):
        dates = _extract_dates("没有日期")
        assert dates == []


class TestDeadlineExtraction:
    def test_deadline_with_date(self):
        text = "限于2024年12月31日前还款"
        deadline = _extract_deadline(text)
        assert "2024" in deadline

    def test_no_deadline(self):
        deadline = _extract_deadline("没有期限的文本")
        assert deadline == ""


class TestKeyFactExtraction:
    def test_extracts_facts(self):
        text = "经审理查明，被告于2024年1月借款10万元。本院认为，被告应当还款。"
        facts = _extract_key_facts(text)
        assert len(facts) >= 1

    def test_empty_text(self):
        facts = _extract_key_facts("")
        assert facts == []


class TestDisputedFactExtraction:
    def test_dispute_marker(self):
        text = "被告对借款金额存在争议。原告对还款时间有异议。"
        disputes = _extract_disputed_facts(text)
        assert len(disputes) >= 1

    def test_no_dispute(self):
        disputes = _extract_disputed_facts("没有争议的文本")
        assert disputes == []
