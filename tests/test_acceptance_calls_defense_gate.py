"""
tests/test_acceptance_calls_defense_gate.py

Test: Acceptance test must call DefenseQualityGate.
"""
import os
import sys

sys.path.insert(0, ".")


def test_acceptance_script_imports_defense_gate():
    """accept_v18_delivery.py must import DefenseQualityGate."""
    script_path = "scripts/accept_v18_delivery.py"
    if not os.path.exists(script_path):
        return

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "DefenseQualityGate" in content, \
        "accept_v18_delivery.py must import/use DefenseQualityGate"
    assert "defense_gate" in content or "defense_result" in content, \
        "accept_v18_delivery.py must call defense gate"


def test_acceptance_script_checks_defense_result():
    """accept_v18_delivery.py must check defense gate result."""
    script_path = "scripts/accept_v18_delivery.py"
    if not os.path.exists(script_path):
        return

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "defense_passed" in content or "defense_result.passed" in content, \
        "accept_v18_delivery.py must check defense gate passed status"
