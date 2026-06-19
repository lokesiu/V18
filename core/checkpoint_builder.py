"""core/checkpoint_builder.py — Build ctx_snapshot JSON from PipelineContext.

Extracts only the fields needed for recovery, excluding large transient
data (raw_texts) that can be recomputed cheaply.
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.fact_card import PipelineContext


def build_ctx_snapshot(ctx: "PipelineContext") -> str:
    """Serialize PipelineContext to a recovery-safe JSON string.

    Excludes raw_texts (recomputable from files).  Includes:
    - task metadata
    - fact_card / strategy_card / distilled_card (structured results)
    - filled_templates keys (not full content — too large)
    - rendered_files list
    - raw_texts_len + raw_texts_hash (for validation)
    - errors
    """
    snapshot = {
        "task_id": ctx.task_id,
        "identity": ctx.identity,
        "goal": ctx.goal,
        "input_dir": ctx.input_dir,
        "output_dir": ctx.output_dir,
        "file_list": ctx.file_list,
        "errors": list(ctx.errors),
    }

    # raw_texts validation (not the content itself)
    if ctx.raw_texts:
        combined = "\n".join(ctx.raw_texts)
        snapshot["raw_texts_len"] = len(combined)
        snapshot["raw_texts_hash"] = hashlib.md5(combined.encode("utf-8")).hexdigest()[:8]

    # Structured results
    if ctx.fact_card:
        snapshot["fact_card"] = ctx.fact_card.to_dict()
    if ctx.strategy_card:
        snapshot["strategy_card"] = ctx.strategy_card.to_dict()
    if ctx.distilled_card:
        snapshot["distilled_card"] = ctx.distilled_card.to_dict()

    # Filled templates — keys only (content is too large for checkpoint)
    filled = getattr(ctx, "_filled_templates", None)
    if filled and isinstance(filled, dict):
        snapshot["filled_templates_keys"] = list(filled.keys())

    # Rendered files
    rendered = getattr(ctx, "_rendered_files", None)
    if rendered:
        snapshot["rendered_files"] = list(rendered)

    return json.dumps(snapshot, ensure_ascii=False)


def restore_ctx_from_snapshot(snapshot_json: str, ctx: "PipelineContext") -> "PipelineContext":
    """Restore checkpointed fields into an existing PipelineContext.

    Only overwrites fields that exist in the snapshot; leaves others
    untouched (especially raw_texts which must be recomputed).
    """
    data = json.loads(snapshot_json)

    if "fact_card" in data and data["fact_card"]:
        from core.fact_card import FactCard
        ctx.fact_card = FactCard.from_dict(data["fact_card"])

    if "strategy_card" in data and data["strategy_card"]:
        from core.fact_card import StrategyCard
        ctx.strategy_card = StrategyCard.from_dict(data["strategy_card"])

    if "distilled_card" in data and data["distilled_card"]:
        from core.fact_card import DistilledCard
        ctx.distilled_card = DistilledCard.from_dict(data["distilled_card"])

    if "rendered_files" in data:
        ctx._rendered_files = data["rendered_files"]

    if "errors" in data:
        ctx.errors = list(data["errors"])

    return ctx
