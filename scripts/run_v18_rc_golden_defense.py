"""
scripts/run_v18_rc_golden_defense.py

Golden Defense Case runner - called by run_v18_rc_golden_defense.ps1
Runs defense quality gate and reports results.
Must exit non-zero on any failure.
"""
import sys
import os
import json

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)


def main():
    output_dir = "outputs/golden_defense_case"

    print("=== Defense Quality Gate Check ===")
    print(f"Output directory: {output_dir}")
    print()

    # Check output directory exists
    if not os.path.isdir(output_dir):
        print(f"[FAIL] Output directory does not exist: {output_dir}")
        return 1

    customer_dir = os.path.join(output_dir, "customer")
    if not os.path.isdir(customer_dir):
        print(f"[FAIL] Customer directory does not exist: {customer_dir}")
        return 1

    # Read AI mode from manifest
    manifest_path = os.path.join(output_dir, "ai_run_manifest.json")
    ai_mode = "unknown"
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        ai_mode = manifest.get("ai_mode", "unknown")
        print(f"AI Mode: {ai_mode}")
    else:
        print("[WARN] ai_run_manifest.json not found")

    # Run defense quality gate
    from core.quality.defense_quality_gate import DefenseQualityGate

    gate = DefenseQualityGate()
    result = gate.run_checks(output_dir, ai_mode)

    print()
    print(result.summary())
    print()

    failed_checks = []
    for check in result.checks:
        status = "[PASS]" if check.passed else "[FAIL]"
        print(f"  {status} {check.check_name}: {check.message}")
        if not check.passed:
            failed_checks.append(check)

    print()

    if not result.passed:
        print(f"Defense quality gate FAILED: {len(failed_checks)} check(s) failed")
        for fc in failed_checks:
            print(f"  - {fc.check_name}: {fc.message}")
            if fc.details:
                print(f"    Details: {fc.details}")
            if fc.remediation:
                print(f"    Remediation: {fc.remediation}")
        return 1

    print("Defense quality gate PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
