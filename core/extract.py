"""
extract.py - Fact Extraction (API-A Interface)

Extracts structured facts from raw text using either:
1. API-A (remote LLM) when configured via environment variable
2. Local regex fallback (default) for basic pattern extraction

The local fallback extracts:
- Case IDs (e.g., (2024)京01民初123号)
- Court names
- Party names and roles
- Monetary amounts (人民币XX元)
- Dates and deadlines
"""
from __future__ import annotations
import os
import re
from typing import List, Optional, Tuple

from core.fact_card import FactCard, Party, SourceRef, PipelineContext


# ---------------------------------------------------------------------------
# Regex patterns for local fact extraction
# ---------------------------------------------------------------------------

# Case ID patterns: (2024)京01民初123号, (2023)粤03民终456号, etc.
CASE_ID_PATTERN = re.compile(
    r'[（(]\s*\d{4}\s*[）)]\s*'           # (2024)
    r'[\u4e00-\u9fff]{1,6}'               # 京/粤/沪 etc.
    r'\d{1,4}'                             # 01/03 etc.
    r'[\u4e00-\u9fff]{2,4}'               # 民初/民终/刑初 etc.
    r'\d{1,6}'                             # 123
    r'号'                                   # 号
)

# Court name patterns
COURT_PATTERNS = [
    re.compile(r'([\u4e00-\u9fff]{2,10}人民法院)'),
    re.compile(r'最高人民法院'),
    re.compile(r'([\u4e00-\u9fff]+高级人民法院)'),
    re.compile(r'([\u4e00-\u9fff]+中级人民法院)'),
    re.compile(r'([\u4e00-\u9fff]+基层人民法院)'),
    re.compile(r'([\u4e00-\u9fff]{2,10}仲裁委员会)'),
]

# Party name patterns - look for plaintiff/defendant/applicant patterns
PARTY_PATTERNS = [
    # 原告：XXX / 被告：XXX
    re.compile(r'(原告|被告|申请人|被申请人|投诉人|被投诉人|上诉人|被上诉人|申请执行人|被执行人)\s*[:：]\s*([\u4e00-\u9fff\w（）\(\)]{2,30})'),
    # 原告(反诉被告)：XXX
    re.compile(r'(原告|被告|申请人|被申请人)\s*[（(][^）)]+[）)]\s*[:：]\s*([\u4e00-\u9fff\w（）\(\)]{2,30})'),
]

# Amount patterns
AMOUNT_PATTERNS = [
    re.compile(r'(?:人民币|RMB|￥|¥)\s*([\d,]+(?:\.\d{1,2})?)\s*(?:元|万元)'),
    re.compile(r'([\d,]+(?:\.\d{1,2})?)\s*(?:万元|元)'),
    re.compile(r'(?:赔偿|支付|返还|补偿|罚款|违约金)\s*(?:人民币)?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:元|万元)'),
]

# Date patterns
DATE_PATTERNS = [
    re.compile(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'),
    re.compile(r'(\d{4})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})'),
]

# Deadline patterns
DEADLINE_KEYWORDS = ['截止', '期限', '届满', '到期', '限于', '应于', '须在', '十五日内', '三十日内', '六十日内']


def _extract_case_ids(text: str) -> List[str]:
    """Extract case ID patterns from text."""
    matches = CASE_ID_PATTERN.findall(text)
    # Normalize: ensure proper format
    results = []
    for m in matches:
        normalized = m.strip()
        if normalized not in results:
            results.append(normalized)
    return results


def _extract_court(text: str) -> str:
    """Extract the most likely court name from text."""
    for pattern in COURT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0) if not match.groups() else match.group(1)
    return ""


def _extract_parties(text: str) -> List[Party]:
    """Extract party names and roles from text."""
    parties = []
    seen = set()

    for pattern in PARTY_PATTERNS:
        for match in pattern.finditer(text):
            role = match.group(1)
            name = match.group(2).strip()
            # Clean up name - remove trailing punctuation
            name = re.sub(r'[，。,.\s]+$', '', name)
            key = f"{role}:{name}"
            if key not in seen and len(name) >= 2:
                seen.add(key)
                parties.append(Party(name=name, role=role))

    return parties


def _extract_amounts(text: str) -> List[str]:
    """Extract monetary amounts from text."""
    amounts = []
    for pattern in AMOUNT_PATTERNS:
        for match in pattern.finditer(text):
            # Get the full match for context
            full_match = match.group(0)
            if full_match not in amounts:
                amounts.append(full_match)
    return amounts


def _extract_dates(text: str) -> List[str]:
    """Extract dates from text."""
    dates = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            year = match.group(1)
            month = match.group(2).zfill(2)
            day = match.group(3).zfill(2)
            date_str = f"{year}年{month}月{day}日"
            if date_str not in dates:
                dates.append(date_str)
    return dates


def _extract_deadline(text: str) -> str:
    """Extract deadline information from text.
    
    Only returns actual dates in YYYY年MM月DD日 format.
    Returns empty string if no deadline date found.
    """
    for keyword in DEADLINE_KEYWORDS:
        idx = text.find(keyword)
        if idx != -1:
            # Extract surrounding context (30 chars before and 80 after)
            start = max(0, idx - 30)
            end = min(len(text), idx + 80)
            snippet = text[start:end].strip()
            # Try to find a date in this snippet
            for pattern in DATE_PATTERNS:
                date_match = pattern.search(snippet)
                if date_match:
                    year = date_match.group(1)
                    month = date_match.group(2).zfill(2)
                    day = date_match.group(3).zfill(2)
                    return f"{year}年{month}月{day}日"
            # Don't return snippet - only return actual dates
            break
    return ""


def _extract_key_facts(text: str) -> List[str]:
    """Extract key factual statements from text."""
    facts = []
    # Look for sentences with key legal markers
    key_markers = [
        '经审理查明', '本院认为', '查明', '事实如下',
        '一、', '二、', '三、', '1.', '2.', '3.',
        '根据', '依据', '鉴于', '因', '由于',
    ]

    sentences = re.split(r'[。！？\n]', text)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        for marker in key_markers:
            if marker in sentence:
                facts.append(sentence.rstrip('，。,'))
                break

    # Limit to top 10 most relevant
    return facts[:10]


def _extract_disputed_facts(text: str) -> List[str]:
    """Extract facts that are explicitly disputed."""
    disputes = []
    dispute_markers = ['争议', '分歧', '异议', '认为.*不.*', '否认', '反驳', '抗辩']

    for marker in dispute_markers:
        pattern = re.compile(f'[^。！？]*{marker}[^。！？]*[。]', re.DOTALL)
        for match in pattern.finditer(text):
            fact = match.group(0).strip()
            if len(fact) > 10 and fact not in disputes:
                disputes.append(fact)

    return disputes[:5]


def _extract_source_refs(text: str, file_name: str) -> List[SourceRef]:
    """Create source references for extracted facts."""
    refs = []
    # Simple: reference the whole file as a source
    if text.strip():
        excerpt = text[:200] + "..." if len(text) > 200 else text
        refs.append(SourceRef(
            file_name=file_name,
            page=None,
            excerpt=excerpt,
        ))
    return refs


def _local_extract(texts: List[str], file_list: List[str]) -> FactCard:
    """
    Local regex-based fact extraction.
    Processes all raw texts and produces a FactCard.
    """
    fact_card = FactCard()
    all_amounts = []
    all_dates = []
    all_parties = []
    all_refs = []

    for i, text in enumerate(texts):
        if not text.strip() or text.startswith("["):
            continue

        file_name = os.path.basename(file_list[i]) if i < len(file_list) else f"file_{i}"

        # Extract case IDs (use the first one found)
        case_ids = _extract_case_ids(text)
        if case_ids and not fact_card.case_id:
            fact_card.case_id = case_ids[0]

        # Extract court name
        court = _extract_court(text)
        if court and not fact_card.court:
            fact_card.court = court

        # Extract parties
        parties = _extract_parties(text)
        all_parties.extend(parties)

        # Extract amounts
        amounts = _extract_amounts(text)
        all_amounts.extend(amounts)

        # Extract dates
        dates = _extract_dates(text)
        all_dates.extend(dates)

        # Extract deadline
        deadline = _extract_deadline(text)
        if deadline and not fact_card.deadline:
            fact_card.deadline = deadline

        # Extract key facts
        key_facts = _extract_key_facts(text)
        fact_card.key_facts.extend(key_facts)

        # Extract disputed facts
        disputed = _extract_disputed_facts(text)
        fact_card.disputed_facts.extend(disputed)

        # Create source references
        refs = _extract_source_refs(text, file_name)
        all_refs.extend(refs)

    # Deduplicate parties
    seen_parties = set()
    for party in all_parties:
        key = f"{party.role}:{party.name}"
        if key not in seen_parties:
            seen_parties.add(key)
            fact_card.parties.append(party)

    # Set amount (use the largest one found)
    if all_amounts:
        fact_card.amount = all_amounts[0]

    # Deduplicate key facts and disputed facts
    fact_card.key_facts = list(dict.fromkeys(fact_card.key_facts))[:10]
    fact_card.disputed_facts = list(dict.fromkeys(fact_card.disputed_facts))[:5]

    # Set source references
    fact_card.source_refs = all_refs

    return fact_card


def _try_api_a(texts: List[str], file_list: List[str]) -> Optional[FactCard]:
    """
    Attempt to use API-A for fact extraction.
    Returns None if API-A is not configured or fails.
    """
    api_key = os.environ.get("API_A_KEY", "")
    api_base = os.environ.get("API_A_BASE_URL", "")

    if not api_key or not api_base:
        return None

    try:
        from core.providers.api_a_client import ApiAClient
        client = ApiAClient(api_key=api_key, base_url=api_base)

        # Combine texts for sending to API
        combined_text = "\n\n---\n\n".join(
            f"=== 文件: {file_list[i] if i < len(file_list) else 'unknown'} ===\n{text}"
            for i, text in enumerate(texts)
            if text.strip() and not text.startswith("[")
        )

        if not combined_text.strip():
            return None

        # Call API-A for structured extraction
        # Note: enhance_facts expects a FactCard and raw_texts list
        from core.fact_card import FactCard
        empty_card = FactCard()
        enhanced = client.enhance_facts(empty_card, [combined_text])
        result = enhanced.to_dict() if enhanced else None

        if result and isinstance(result, dict):
            return FactCard.from_dict(result)

        return None

    except ImportError:
        return None
    except Exception:
        return None


def extract_facts(ctx: PipelineContext) -> PipelineContext:
    """
    Main entry point for fact extraction.
    
    1. Tries API-A first if configured
    2. Falls back to local regex extraction
    3. Populates ctx.fact_card with extracted facts
    """
    ctx.log("开始事实提取...")

    if not ctx.raw_texts:
        ctx.add_error("没有原始文本可供提取")
        return ctx

    # Set identity on the fact card if available
    identity = ctx.identity

    # Try API-A first
    fact_card = _try_api_a(ctx.raw_texts, ctx.file_list)

    if fact_card:
        ctx.log("使用API-A成功提取事实")
    else:
        ctx.log("使用本地正则提取（API-A未配置或不可用）")
        fact_card = _local_extract(ctx.raw_texts, ctx.file_list)

    # Set identity from context
    if identity:
        fact_card.identity = identity

    ctx.fact_card = fact_card

    # Log extraction results
    ctx.log(f"案号: {fact_card.case_id or '未识别'}")
    ctx.log(f"法院: {fact_card.court or '未识别'}")
    ctx.log(f"当事人: {len(fact_card.parties)} 个")
    ctx.log(f"金额: {fact_card.amount or '未识别'}")
    ctx.log(f"关键事实: {len(fact_card.key_facts)} 条")
    ctx.log(f"争议事实: {len(fact_card.disputed_facts)} 条")
    ctx.log(f"来源引用: {len(fact_card.source_refs)} 个")

    return ctx
