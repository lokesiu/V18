"""
tests/test_golden_case_passes_defense_gate.py

Test: Golden Case must pass Defense Quality Gate.
"""
import os
import sys
import json

sys.path.insert(0, ".")

from core.quality.defense_quality_gate import DefenseQualityGate


def test_golden_case_defense_gate_passes():
    """Golden Case must pass Defense Quality Gate."""
    case_dir = "outputs/golden_defense_case"
    if not os.path.isdir(case_dir):
        return  # Skip if golden case not run

    customer_dir = os.path.join(case_dir, "customer")
    if not os.path.isdir(customer_dir):
        return

    # Skip if distilled_card.json doesn't exist (golden case not fully run)
    distilled_path = os.path.join(case_dir, "_internal", "distilled_card.json")
    if not os.path.exists(distilled_path):
        return  # Skip - golden case data not available

    # Read AI mode
    manifest_path = os.path.join(case_dir, "ai_run_manifest.json")
    ai_mode = "unknown"
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        ai_mode = manifest.get("ai_mode", "unknown")

    gate = DefenseQualityGate()
    result = gate.run_checks(case_dir, ai_mode)

    failed_checks = [c for c in result.checks if not c.passed]
    assert result.passed, \
        f"Defense gate failed: {[c.check_name for c in failed_checks]}"


def test_golden_case_ai_mode_is_real():
    """Golden Case AI mode must be real_ai."""
    case_dir = "outputs/golden_defense_case"
    manifest_path = os.path.join(case_dir, "ai_run_manifest.json")
    if not os.path.exists(manifest_path):
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    ai_mode = manifest.get("ai_mode", "")
    assert ai_mode == "real_ai", f"Expected real_ai, got {ai_mode}"


def test_golden_case_has_required_files():
    """Golden Case must have all required files."""
    customer_dir = "outputs/golden_defense_case/customer"
    if not os.path.isdir(customer_dir):
        return

    required = ["*.docx", "*.pdf", "*.zip"]
    from pathlib import Path
    for pattern in required:
        files = list(Path(customer_dir).glob(pattern))
        assert len(files) > 0, f"No {pattern} files found"
