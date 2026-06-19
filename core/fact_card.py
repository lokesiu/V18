"""
fact_card.py - THE SHARED DATA CONTRACT

All other modules depend on these dataclasses.
Every pipeline stage reads/writes through these structures.
Serialization is JSON-based for persistence and inter-process communication.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any
import json
from datetime import datetime


@dataclass
class Party:
    name: str = ""
    role: str = ""  # 原告/被告/申请人/被申请人/投诉人/被投诉人

    def to_dict(self) -> dict:
        return {"name": self.name, "role": self.role}

    @classmethod
    def from_dict(cls, d: dict) -> Party:
        return cls(
            name=d.get("name", ""),
            role=d.get("role", ""),
        )


@dataclass
class SourceRef:
    file_name: str = ""
    page: Optional[int] = None
    excerpt: str = ""

    def to_dict(self) -> dict:
        return {
            "file_name": self.file_name,
            "page": self.page,
            "excerpt": self.excerpt,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SourceRef:
        return cls(
            file_name=d.get("file_name", ""),
            page=d.get("page"),
            excerpt=d.get("excerpt", ""),
        )


@dataclass
class FactCard:
    case_id: str = ""
    court: str = ""
    parties: List[Party] = field(default_factory=list)
    identity: str = ""  # 投诉方/起诉方/被诉方/行政复议申请人/整理证据
    amount: str = ""
    deadline: str = ""
    key_facts: List[str] = field(default_factory=list)
    disputed_facts: List[str] = field(default_factory=list)
    missing_materials: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    source_refs: List[SourceRef] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON persistence."""
        return {
            "case_id": self.case_id,
            "court": self.court,
            "parties": [p.to_dict() for p in self.parties],
            "identity": self.identity,
            "amount": self.amount,
            "deadline": self.deadline,
            "key_facts": list(self.key_facts),
            "disputed_facts": list(self.disputed_facts),
            "missing_materials": list(self.missing_materials),
            "conflicts": list(self.conflicts),
            "source_refs": [s.to_dict() for s in self.source_refs],
        }

    @classmethod
    def from_dict(cls, d: dict) -> FactCard:
        """Deserialize from dict."""
        return cls(
            case_id=d.get("case_id", ""),
            court=d.get("court", ""),
            parties=[Party.from_dict(p) for p in d.get("parties", [])],
            identity=d.get("identity", ""),
            amount=d.get("amount", ""),
            deadline=d.get("deadline", ""),
            key_facts=list(d.get("key_facts", [])),
            disputed_facts=list(d.get("disputed_facts", [])),
            missing_materials=list(d.get("missing_materials", [])),
            conflicts=list(d.get("conflicts", [])),
            source_refs=[SourceRef.from_dict(s) for s in d.get("source_refs", [])],
        )


@dataclass
class ActionAdvice:
    action: str = ""
    priority: str = ""  # S/A/B/C/D
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "priority": self.priority,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ActionAdvice:
        return cls(
            action=d.get("action", ""),
            priority=d.get("priority", ""),
            reasoning=d.get("reasoning", ""),
        )


@dataclass
class DraftDocument:
    doc_type: str = ""  # 投诉状/起诉状/答辩状/行政复议申请书
    title: str = ""
    content: str = ""

    def to_dict(self) -> dict:
        return {
            "doc_type": self.doc_type,
            "title": self.title,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DraftDocument:
        return cls(
            doc_type=d.get("doc_type", ""),
            title=d.get("title", ""),
            content=d.get("content", ""),
        )


@dataclass
class StrategyCard:
    situation_assessment: str = ""
    action_advice: List[ActionAdvice] = field(default_factory=list)
    evidence_gap: List[str] = field(default_factory=list)
    draft_documents: List[DraftDocument] = field(default_factory=list)
    risk_warnings: List[str] = field(default_factory=list)
    sabcd_rating: str = ""  # S/A/B/C/D rating

    def to_dict(self) -> dict:
        return {
            "situation_assessment": self.situation_assessment,
            "action_advice": [a.to_dict() for a in self.action_advice],
            "evidence_gap": list(self.evidence_gap),
            "draft_documents": [d.to_dict() for d in self.draft_documents],
            "risk_warnings": list(self.risk_warnings),
            "sabcd_rating": self.sabcd_rating,
        }

    @classmethod
    def from_dict(cls, d: dict) -> StrategyCard:
        return cls(
            situation_assessment=d.get("situation_assessment", ""),
            action_advice=[ActionAdvice.from_dict(a) for a in d.get("action_advice", [])],
            evidence_gap=list(d.get("evidence_gap", [])),
            draft_documents=[DraftDocument.from_dict(dd) for dd in d.get("draft_documents", [])],
            risk_warnings=list(d.get("risk_warnings", [])),
            sabcd_rating=d.get("sabcd_rating", ""),
        )


@dataclass
class DistilledCard:
    fact_card: FactCard = field(default_factory=FactCard)
    strategy_card: StrategyCard = field(default_factory=StrategyCard)

    def to_dict(self) -> dict:
        return {
            "fact_card": self.fact_card.to_dict(),
            "strategy_card": self.strategy_card.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> DistilledCard:
        return cls(
            fact_card=FactCard.from_dict(d.get("fact_card", {})),
            strategy_card=StrategyCard.from_dict(d.get("strategy_card", {})),
        )

    def save(self, path: str) -> None:
        """Save to JSON file."""
        data = self.to_dict()
        data["_meta"] = {
            "saved_at": datetime.now().isoformat(),
            "version": "V18",
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> DistilledCard:
        """Load from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Strip metadata if present
        data.pop("_meta", None)
        return cls.from_dict(data)


@dataclass
class PipelineContext:
    input_dir: str = ""
    output_dir: str = ""
    identity: str = ""  # 投诉方/起诉方/被诉方/行政复议申请人/整理证据
    goal: str = ""  # 投诉举报/起诉立案/应诉答辩/行政复议/证据整理
    purpose: str = ""  # 用户输入的具体目的（可选）
    fact_card: Optional[FactCard] = None
    strategy_card: Optional[StrategyCard] = None
    distilled_card: Optional[DistilledCard] = None
    errors: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    case_label: str = ""
    raw_texts: List[str] = field(default_factory=list)  # raw extracted text from input files
    file_list: List[str] = field(default_factory=list)  # list of input file paths

    # ── Task metadata (Phase 2) ──
    task_id: str = ""
    task_status: str = ""       # mirrors task_store status
    current_step: int = 0       # 0-based step index
    created_at: str = ""
    updated_at: str = ""
    error_message: str = ""
    retry_count: int = 0

    def log(self, msg: str) -> None:
        """Append timestamped log entry."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {msg}")

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.log(f"ERROR: {msg}")

    def to_dict(self) -> dict:
        """Serialize context to dict (excluding large raw_texts for brevity)."""
        return {
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
            "identity": self.identity,
            "goal": self.goal,
            "purpose": self.purpose,
            "fact_card": self.fact_card.to_dict() if self.fact_card else None,
            "strategy_card": self.strategy_card.to_dict() if self.strategy_card else None,
            "distilled_card": self.distilled_card.to_dict() if self.distilled_card else None,
            "errors": list(self.errors),
            "logs": list(self.logs),
            "case_label": self.case_label,
            "file_list": list(self.file_list),
            "raw_text_count": len(self.raw_texts),
            "task_id": self.task_id,
            "task_status": self.task_status,
            "current_step": self.current_step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PipelineContext:
        """Deserialize context from dict."""
        return cls(
            input_dir=d.get("input_dir", ""),
            output_dir=d.get("output_dir", ""),
            identity=d.get("identity", ""),
            goal=d.get("goal", ""),
            purpose=d.get("purpose", ""),
            fact_card=FactCard.from_dict(d["fact_card"]) if d.get("fact_card") else None,
            strategy_card=StrategyCard.from_dict(d["strategy_card"]) if d.get("strategy_card") else None,
            distilled_card=DistilledCard.from_dict(d["distilled_card"]) if d.get("distilled_card") else None,
            errors=list(d.get("errors", [])),
            logs=list(d.get("logs", [])),
            case_label=d.get("case_label", ""),
            file_list=list(d.get("file_list", [])),
            task_id=d.get("task_id", ""),
            task_status=d.get("task_status", ""),
            current_step=d.get("current_step", 0),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            error_message=d.get("error_message", ""),
            retry_count=d.get("retry_count", 0),
        )
