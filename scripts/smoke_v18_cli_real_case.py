"""Smoke test: Verify V18 CLI works with real case data."""
import sys
import os
import subprocess
from pathlib import Path


def test_cli_doctor():
    """Test: python -m core.runner doctor"""
    result = subprocess.run(
        [sys.executable, "-m", "core.runner", "doctor"],
        capture_output=True, text=True, cwd="D:\\codex\\V18"
    )
    assert result.returncode == 0, f"doctor failed: {result.stderr}"


def test_cli_analyze():
    """Test: python -m core.runner analyze with fixture data."""
    input_dir = "fixtures"
    output_dir = "outputs/smoke_test_001"

    result = subprocess.run([
        sys.executable, "-m", "core.runner", "analyze",
        "--input", input_dir,
        "--identity", "被诉方",
        "--goal", "应诉答辩",
        "--out", output_dir
    ], capture_output=True, text=True, cwd="D:\\codex\\V18")

    print(f"  analyze returncode: {result.returncode}")
    print(f"  stdout: {result.stdout[:500]}")
    if result.stderr:
        print(f"  stderr: {result.stderr[:500]}")


if __name__ == "__main__":
    print("=== V18 CLI Smoke Test ===")
    try:
        test_cli_doctor()
        print("  [PASS] doctor")
    except Exception as e:
        print(f"  [FAIL] doctor: {e}")

    test_cli_analyze()
