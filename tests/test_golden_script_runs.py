"""
tests/test_golden_script_runs.py

Test: Golden Case PS1 script doesn't contain raw Python syntax.
"""
import os
import re


def test_ps1_no_raw_python():
    """PS1 must not contain bare Python code outside python -c."""
    ps1_path = "scripts/run_v18_rc_golden_defense.ps1"
    if not os.path.exists(ps1_path):
        return  # Skip if file doesn't exist

    with open(ps1_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for Python-only syntax that would break PowerShell
    python_patterns = [
        r"^\s*import\s+\w+",  # import statements
        r"^\s*from\s+\w+\s+import",  # from imports
        r"^\s*def\s+\w+\s*\(",  # function defs
        r"^\s*class\s+\w+",  # class defs
        r"^\s*if\s+__name__\s*==",  # if __name__ == "__main__"
    ]

    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        # Skip lines inside python -c "..." blocks
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("python "):
            continue

        for pattern in python_patterns:
            if re.match(pattern, stripped):
                assert False, f"PS1 line {i} contains bare Python: {stripped[:50]}"


def test_ps1_calls_python_script():
    """PS1 should call run_v18_rc_golden_defense.py for defense gate."""
    ps1_path = "scripts/run_v18_rc_golden_defense.ps1"
    if not os.path.exists(ps1_path):
        return

    with open(ps1_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must call the Python helper script
    assert "run_v18_rc_golden_defense.py" in content, \
        "PS1 should call run_v18_rc_golden_defense.py"


def test_python_script_exists():
    """The Python helper script must exist."""
    assert os.path.exists("scripts/run_v18_rc_golden_defense.py"), \
        "run_v18_rc_golden_defense.py must exist"
