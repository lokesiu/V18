"""
tests/test_quality_gate_no_false_pass.py

Test: Quality gate must FAIL when any CheckResult.passed=False.
"""
import os
import sys

sys.path.insert(0, ".")

from core.quality.final_artifact_auditor import (
    CheckResult, AuditReport, audit_artifacts
)
from core.quality.defense_quality_gate import DefenseQualityGate


def test_audit_report_fails_on_any_check_false():
    """AuditReport.passed must be False if any check is False."""
    report = AuditReport(checks=[
        CheckResult(check_name="test1", passed=True, message="ok"),
        CheckResult(check_name="test2", passed=False, message="fail"),
    ])
    assert not report.passed, "AuditReport should fail when any check fails"


def test_audit_report_passes_only_when_all_pass():
    """AuditReport.passed must be True only when all checks pass."""
    report = AuditReport(checks=[
        CheckResult(check_name="test1", passed=True, message="ok"),
        CheckResult(check_name="test2", passed=True, message="ok"),
    ])
    assert report.passed, "AuditReport should pass when all checks pass"


def test_defense_gate_fails_on_local_fallback():
    """Defense gate must fail when AI mode is local_fallback."""
    gate = DefenseQualityGate()
    # Create a temp directory with minimal structure
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        customer_dir = os.path.join(tmpdir, "customer")
        os.makedirs(customer_dir)
        # Create minimal files
        with open(os.path.join(customer_dir, "test.docx"), "w") as f:
            f.write("test")

        result = gate.run_checks(tmpdir, ai_mode="local_fallback")
        assert not result.passed, "Defense gate should fail on local_fallback"
        assert any(
            "FAIL_NO_REAL_AI" in c.message
            for c in result.checks if not c.passed
        ), "Should have FAIL_NO_REAL_AI check"


def test_step8_adds_error_on_failed_check():
    """Step 8 must add error to ctx when audit fails."""
    from core.fact_card import PipelineContext
    from core.pipeline.step8_quality_gate import step8_quality_gate

    # Create a minimal case with no customer directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = PipelineContext(output_dir=tmpdir)
        ctx = step8_quality_gate(ctx)
        # Should have error about missing customer directory
        assert len(ctx.errors) > 0, "Step 8 should add error when customer dir missing"
