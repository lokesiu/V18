"""core/text_utils.py — Shared text processing utilities.

Consolidates duplicated text-cleaning, tag-stripping, and party-analysis
logic from step7_render, step6_llm_generate, api_b_client, and distiller.
"""
from __future__ import annotations

import re
from typing import List, Set


# ══════════════════════════════════════════════════════════════════════
# Precompiled regex patterns (compiled once, reused everywhere)
# ══════════════════════════════════════════════════════════════════════

# LLM output cleaning
_RE_BRACKET_FILL = re.compile(r'\[请填写[^\]]*\]')
_RE_BRACKET_SUPPLEMENT = re.compile(r'\[请补充[^\]]*\]')
_RE_BARE_FILL = re.compile(r'请填写[^\n，。；]*')
RE_BARE_SUPPLEMENT = re.compile(r'请补充[^\n，。；]*')
_RE_MD_BOLD = re.compile(r'\*\*([^*]+)\*\*')
_RE_MD_HEADING = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_RE_MD_LIST = re.compile(r'^\s*[-*]\s+', re.MULTILINE)
_RE_MD_CODE = re.compile(r'`([^`]+)`')
_RE_LLM_OPENING = re.compile(r'^好的[，,。.!！\s]*')
_RE_LLM_LAWYER = re.compile(r'资深诉讼律师[^。！\n]*[。！\n]?')
_RE_LLM_WRITING = re.compile(r'为您撰写以下[：:]?\s*\n?')
_RE_LLM_HERE = re.compile(r'以下是[^。！\n]*[。！\n]?\s*\n?')
_RE_LLM_ACCORDING = re.compile(r'根据[^，。\n]*要求[，,]?\s*')
_RE_VAGUE_LAW = re.compile(r'《[^》]+》相关规定')
RE_VAGUE_LAW_SUFFIX = re.compile(r'的相关规定')
_RE_LEGAL_DOC_TITLE = re.compile(r'^法律文书\s*\n?', re.MULTILINE)
_RE_LEGAL_DOC_NEWLINE = re.compile(r'法律文书\s*\n民事')
_RE_MULTI_NEWLINE = re.compile(r'\n{3,}')

# Chinese text extraction
_RE_CHINESE_2PLUS = re.compile(r'[\u4e00-\u9fff]{2,}')
_RE_DIGITS = re.compile(r'\d+')

# Tag stripping
_RE_DISTILLER_TAGS = re.compile(r'【(待核对|争议|待补充|冲突)】')

# Personal info extraction
_RE_GENDER = re.compile(r'([男女])')
_RE_BIRTH = re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日出生')
_RE_ADDRESS = re.compile(r'住([^\s，,。；]+)')
_RE_ID_NUMBER = re.compile(r'身份证号[：:]?\s*(\d{17}[\dX])')
_RE_PHONE = re.compile(r'(?:电话|联系电话)[：:]?\s*(1[3-9]\d{9})')


# ══════════════════════════════════════════════════════════════════════
# Stop words for fact-source matching
# ══════════════════════════════════════════════════════════════════════

STOP_WORDS: frozenset = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
    "看", "好", "自己", "这", "他", "她", "它", "们", "那", "被", "从", "把",
})


# ══════════════════════════════════════════════════════════════════════
# LLM output cleaning
# ══════════════════════════════════════════════════════════════════════

def clean_llm_output(content: str) -> str:
    """Clean LLM-generated text: remove Markdown, conversational openers, vague citations."""
    if not content:
        return content

    # 1. Remove Markdown
    content = _RE_MD_BOLD.sub(r'\1', content)
    content = _RE_MD_HEADING.sub('', content)
    content = _RE_MD_LIST.sub('', content)
    content = _RE_MD_CODE.sub(r'\1', content)

    # 2. Remove conversational openers
    content = _RE_LLM_OPENING.sub('', content)
    content = _RE_LLM_LAWYER.sub('', content)
    content = _RE_LLM_WRITING.sub('', content)
    content = _RE_LLM_HERE.sub('', content)
    content = _RE_LLM_ACCORDING.sub('', content)

    # 3. Remove vague legal citations
    content = _RE_VAGUE_LAW.sub('', content)
    content = RE_VAGUE_LAW_SUFFIX.sub('', content)

    # 4. Clean up extra newlines
    content = _RE_MULTI_NEWLINE.sub('\n\n', content)

    return content.strip()


def clean_docx_content(content: str) -> str:
    """Clean content for DOCX rendering: includes all LLM cleaning + placeholder removal."""
    if not content:
        return content

    # Bracket placeholders
    content = _RE_BRACKET_FILL.sub('', content)
    content = _RE_BRACKET_SUPPLEMENT.sub('', content)

    # XXX replacement
    content = content.replace('XXX', '[已脱敏]')

    # Type label replacement
    content = content.replace('类型:', '分类:')
    content = content.replace('类型：', '分类：')

    # Bare placeholder sentences
    content = _RE_BARE_FILL.sub('', content)
    content = RE_BARE_SUPPLEMENT.sub('', content)

    # All LLM cleaning
    content = clean_llm_output(content)

    # Remove generic "法律文书" title
    content = _RE_LEGAL_DOC_TITLE.sub('', content)
    content = _RE_LEGAL_DOC_NEWLINE.sub('民事', content)

    return content.strip()


# ══════════════════════════════════════════════════════════════════════
# Tag stripping
# ══════════════════════════════════════════════════════════════════════

def strip_distiller_tags(text: str) -> str:
    """Remove distiller tags like 【待核对】【争议】【待补充】【冲突】."""
    return _RE_DISTILLER_TAGS.sub('', text).strip()


# ══════════════════════════════════════════════════════════════════════
# Chinese text extraction
# ══════════════════════════════════════════════════════════════════════

def extract_chinese_terms(text: str) -> Set[str]:
    """Extract 2+ character Chinese terms and digit sequences from text."""
    terms = set()
    for match in _RE_CHINESE_2PLUS.finditer(text):
        word = match.group(0)
        if len(word) >= 2 and word not in STOP_WORDS:
            terms.add(word)
    for match in _RE_DIGITS.finditer(text):
        terms.add(match.group(0))
    return terms


# ══════════════════════════════════════════════════════════════════════
# Party analysis
# ══════════════════════════════════════════════════════════════════════

def is_company_name(name: str) -> bool:
    """Check if a party name looks like a company/entity rather than an individual."""
    return any(kw in name for kw in ('公司', '有限', '集团', '企业', '工厂', '商行', '商店', '事务所'))


def extract_personal_info(excerpt: str) -> dict:
    """Extract personal info (gender, birth, address, ID, phone) from a text excerpt.

    Returns dict with keys: gender, birth, address, id_number, phone.
    """
    info = {}

    m = _RE_GENDER.search(excerpt)
    if m:
        info['gender'] = m.group(1)

    m = _RE_BIRTH.search(excerpt)
    if m:
        info['birth'] = f"{m.group(1)}年{m.group(2)}月{m.group(3)}日"

    m = _RE_ADDRESS.search(excerpt)
    if m:
        info['address'] = m.group(1)

    m = _RE_ID_NUMBER.search(excerpt)
    if m:
        info['id_number'] = m.group(1)

    m = _RE_PHONE.search(excerpt)
    if m:
        info['phone'] = m.group(1)

    return info


# ══════════════════════════════════════════════════════════════════════
# ID/phone masking for DOCX output
# ══════════════════════════════════════════════════════════════════════

_RE_STANDALONE_ID = re.compile(r'\d{15}(?:\d{2}[\dX])?')
_RE_STANDALONE_PHONE = re.compile(r'1[3-9]\d{9}')
_RE_STANDALONE_ACCOUNT = re.compile(r'\d{4}[\dX]{12,}')


def mask_sensitive_in_line(line: str) -> str:
    """Mask ID numbers and phone numbers in a line, EXCEPT in info declaration lines."""
    if '身份证号' in line or '联系电话' in line or '电话：' in line:
        return line  # Don't mask in info declaration lines
    line = _RE_STANDALONE_ID.sub('[身份信息已脱敏]', line)
    line = _RE_STANDALONE_PHONE.sub('[电话已脱敏]', line)
    line = _RE_STANDALONE_ACCOUNT.sub('[账号已脱敏]', line)
    return line
