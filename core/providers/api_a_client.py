"""
api_a_client.py - API-A Client for Fact Extraction Enhancement

Calls API-A to enhance fact extraction from raw texts.
Falls back to local regex-based extraction when API is unavailable.
NEVER raises exceptions - always returns a valid FactCard.
"""
from __future__ import annotations

import os
import re
import logging
from typing import List, Optional

from core.fact_card import FactCard, Party, SourceRef

logger = logging.getLogger(__name__)


class ApiAClient:
    """API-A client for fact extraction enhancement."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key: str = api_key or os.environ.get("V18_API_A_KEY", "")
        self.base_url: str = base_url or os.environ.get("V18_API_A_URL", "")
        self._available: bool = bool(self.api_key and self.base_url)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enhance_facts(self, fact_card: FactCard, raw_texts: List[str]) -> FactCard:
        """Call API-A to enhance fact extraction. Returns enhanced FactCard.

        If API is available, sends raw_texts and merges structured results.
        If API is unavailable, uses local regex-based extraction as fallback.
        NEVER raises - always returns a FactCard.
        """
        if not raw_texts:
            return fact_card

        combined = "\n".join(raw_texts)

        if self._available:
            try:
                enhanced = self._call_api(fact_card, combined)
                if enhanced is not None:
                    return enhanced
            except Exception as exc:
                logger.warning("API-A call failed, falling back to local extraction: %s", exc)

        return self._local_extract(fact_card, combined)

    # ------------------------------------------------------------------
    # Internal: API call (stub – real implementation depends on API spec)
    # ------------------------------------------------------------------

    def _call_api(self, fact_card: FactCard, combined_text: str) -> FactCard | None:
        """Attempt to call the remote API-A endpoint.

        Returns enhanced FactCard on success, None on failure.
        This is a stub that can be replaced with actual HTTP calls.
        """
        # Placeholder for actual HTTP call:
        # import httpx
        # payload = {
        #     "raw_text": combined_text,
        #     "existing_facts": fact_card.to_dict(),
        # }
        # resp = httpx.post(
        #     f"{self.base_url}/enhance",
        #     json=payload,
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     timeout=30,
        # )
        # resp.raise_for_status()
        # data = resp.json()
        # return FactCard.from_dict(data)
        return None

    # ------------------------------------------------------------------
    # Internal: Local regex-based extraction
    # ------------------------------------------------------------------

    def _local_extract(self, fact_card: FactCard, text: str) -> FactCard:
        """Extract structured facts using regex patterns.

        Merges extracted values into the existing FactCard, only filling
        fields that are currently empty.
        """
        # Work on a copy to avoid mutating the original
        result = FactCard(
            case_id=fact_card.case_id,
            court=fact_card.court,
            parties=list(fact_card.parties),
            identity=fact_card.identity,
            amount=fact_card.amount,
            deadline=fact_card.deadline,
            key_facts=list(fact_card.key_facts),
            disputed_facts=list(fact_card.disputed_facts),
            missing_materials=list(fact_card.missing_materials),
            conflicts=list(fact_card.conflicts),
            source_refs=list(fact_card.source_refs),
        )

        # --- case_id: (2024)X法号 pattern ---
        if not result.case_id:
            case_id = self._extract_case_id(text)
            if case_id:
                result.case_id = case_id

        # --- court: XX法院 pattern ---
        if not result.court:
            court = self._extract_court(text)
            if court:
                result.court = court

        # --- parties: 原告/被告/申请人/被申请人 patterns ---
        if not result.parties:
            parties = self._extract_parties(text)
            if parties:
                result.parties = parties

        # --- amount: 人民币X元, X万元 pattern ---
        if not result.amount:
            amount = self._extract_amount(text)
            if amount:
                result.amount = amount

        # --- deadline: YYYY年MM月DD日 (deadline-related context) ---
        if not result.deadline:
            deadline = self._extract_deadline(text)
            if deadline:
                result.deadline = deadline

        # --- key_facts: extract sentences with legal keywords ---
        if not result.key_facts:
            facts = self._extract_key_facts(text)
            if facts:
                result.key_facts = facts

        # --- missing_materials: extract "需要补充" / "缺少" patterns ---
        if not result.missing_materials:
            missing = self._extract_missing_materials(text)
            if missing:
                result.missing_materials = missing

        return result

    # ------------------------------------------------------------------
    # Regex extractors
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_case_id(text: str) -> str:
        """Extract case ID matching patterns like (2024)京01民初123号."""
        patterns = [
            # (2024)京01民初123号  (2023)粤03民终456号
            r'[（(]\d{4}[）)][\u4e00-\u9fa5]{1,6}[\u4e00-\u9fa5]{1,8}[\d]+号',
            # 2024京01民初123号
            r'\d{4}[\u4e00-\u9fa5]{1,6}[\u4e00-\u9fa5]{1,8}[\d]+号',
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(0)
        return ""

    @staticmethod
    def _extract_court(text: str) -> str:
        """Extract court name like 北京市朝阳区人民法院."""
        # Match XX人民法院 (most specific patterns first)
        patterns = [
            # 北京市高级人民法院 / 最高人民法院
            r'最高人民法院',
            r'[\u4e00-\u9fa5]{1,10}高级人民法院',
            r'[\u4e00-\u9fa5]{1,10}中级人民法院',
            r'[\u4e00-\u9fa5]{1,10}基层人民法院',
            r'[\u4e00-\u9fa5]{1,10}人民法院',
            # 仲裁委员会
            r'[\u4e00-\u9fa5]{1,10}仲裁委员会',
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(0)
        # Fallback: look for 市XX局 etc (administrative bodies)
        m = re.search(r'[\u4e00-\u9fa5]{2,8}(?:局|委员会|厅)', text)
        if m:
            return m.group(0)
        return ""

    @staticmethod
    def _extract_parties(text: str) -> List[Party]:
        """Extract parties from text patterns like 原告：张三 / 被告：李四."""
        parties: List[Party] = []
        role_map = {
            "原告": "原告",
            "被告": "被告",
            "申请人": "申请人",
            "被申请人": "被申请人",
            "投诉人": "投诉人",
            "被投诉人": "被投诉人",
            "上诉人": "上诉人",
            "被上诉人": "被上诉人",
            "公诉人": "公诉人",
            "第三人": "第三人",
        }
        # Pattern: 原告：张三  or  原告(一)：张三  or  原告1：张三
        for role_cn, role_val in role_map.items():
            pattern = (
                rf'{role_cn}[（(]?[一二三四五六\d]*[）)]?'
                rf'\s*[：:]\s*'
                r'([\u4e00-\u9fa5·]{2,20})'
            )
            for m in re.finditer(pattern, text):
                name = m.group(1).strip()
                # Filter out common false positives
                if name and name not in ("无", "不详", "不明", "略"):
                    parties.append(Party(name=name, role=role_val))
        return parties

    @staticmethod
    def _extract_amount(text: str) -> str:
        """Extract monetary amounts like 人民币12345.67元 or 10万元."""
        patterns = [
            # 人民币X元
            r'人民币\s*[\d,]+\.?\d*\s*元',
            # X万元
            r'[\d,]+\.?\d*\s*万\s*元',
            # X元
            r'[\d,]+\.?\d*\s*元',
            # X万元整
            r'[\d,]+\.?\d*\s*万元整',
        ]
        for pat in patterns:
            matches = re.findall(pat, text)
            if matches:
                # Return the largest amount found
                return max(matches, key=lambda s: len(s))
        return ""

    @staticmethod
    def _extract_deadline(text: str) -> str:
        """Extract deadline date (typically near deadline-related context)."""
        # Look for deadline-related context first
        deadline_context = re.findall(
            r'(?:期限|截止|deadline|到期|届满|最后)[^\d]{0,20}'
            r'(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)',
            text,
        )
        if deadline_context:
            return deadline_context[0].replace(" ", "")

        # Fallback: return any date found that looks like a deadline
        # (prefer dates in the future or near-end of text)
        dates = re.findall(
            r'(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)',
            text,
        )
        if dates:
            return dates[-1].replace(" ", "")
        return ""

    @staticmethod
    def _extract_key_facts(text: str) -> List[str]:
        """Extract key factual sentences from the text."""
        keywords = [
            "经审理", "查明", "认定", "事实", "根据", "证据",
            "合同", "协议", "约定", "违约", "赔偿", "损失",
            "应当", "依法", "判决", "裁决", "裁定",
            "投诉", "举报", "申请", "复议",
        ]
        sentences = re.split(r'[。！？\n]', text)
        facts: List[str] = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 8:
                continue
            if any(kw in sent for kw in keywords):
                facts.append(sent)
                if len(facts) >= 10:
                    break
        return facts

    @staticmethod
    def _extract_missing_materials(text: str) -> List[str]:
        """Extract mentions of missing or needed materials."""
        patterns = [
            r'(?:需要|缺少|缺乏|不足|补充|缺失)\s*[：:]?\s*([\u4e00-\u9fa5、，,]{4,60})',
            r'(?:暂无|尚未提供|未提交)\s*([\u4e00-\u9fa5、，,]{4,60})',
        ]
        materials: List[str] = []
        for pat in patterns:
            for m in re.finditer(pat, text):
                item = m.group(1).strip()
                if item:
                    materials.append(item)
        return materials
