"""
V18 Core Runner - CLI Entry Point
Usage:
    python -m core.runner doctor
    python -m core.runner analyze --input DIR --identity IDENTITY --goal GOAL --out DIR
    python -m core.runner inspect --case DIR
    python -m core.runner package --case DIR
    python -m core.runner selfcheck --case DIR
"""
import argparse
import sys
import os
from pathlib import Path

def cmd_doctor():
    """Check environment and dependencies."""
    print("=== 明证台 V18 Doctor ===")
    
    checks = []
    
    # Check Python version
    checks.append(("Python >= 3.10", sys.version_info >= (3, 10)))
    
    # Check required packages
    try:
        import PySide6
        checks.append(("PySide6", True))
    except ImportError:
        checks.append(("PySide6", False))
    
    try:
        import docx
        checks.append(("python-docx", True))
    except ImportError:
        checks.append(("python-docx", False))
    
    try:
        import openpyxl
        checks.append(("openpyxl", True))
    except ImportError:
        checks.append(("openpyxl", False))
    
    try:
        import yaml
        checks.append(("PyYAML", True))
    except ImportError:
        checks.append(("PyYAML", False))
    
    try:
        import fpdf
        checks.append(("fpdf2", True))
    except ImportError:
        checks.append(("fpdf2", False))
    
    try:
        import httpx
        checks.append(("httpx", True))
    except ImportError:
        checks.append(("httpx", False))
    
    # Check directories
    for d in ["app", "core", "templates", "prompts", "outputs", "raw_materials"]:
        checks.append((f"Directory: {d}", Path(d).exists()))
    
    # Check template files
    for t in ["common_case_assessment.yaml", "action_advice.yaml", "evidence_catalog.yaml"]:
        checks.append((f"Template: {t}", Path(f"templates/{t}").exists()))
    
    # Check prompt files
    for p in ["api_a_fact_extract.txt", "api_b_strategy_writer.txt", "distill_final_context.txt"]:
        checks.append((f"Prompt: {p}", Path(f"prompts/{p}").exists()))
    
    # Print results
    all_ok = True
    for name, ok in checks:
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status} {name}")
        if not ok:
            all_ok = False
    
    # Check API configuration
    print()
    print("--- AI API Configuration ---")
    
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    api_base = os.environ.get("DEEPSEEK_BASE_URL", "")
    model_extract = os.environ.get("DEEPSEEK_MODEL_EXTRACT", "")
    model_strategy = os.environ.get("DEEPSEEK_MODEL_STRATEGY", "")
    
    if api_key:
        print(f"  [OK] DEEPSEEK_API_KEY: configured ({api_key[:8]}...)")
    else:
        print(f"  [INFO] DEEPSEEK_API_KEY: not configured (local fallback mode)")
    
    if api_base:
        print(f"  [OK] DEEPSEEK_BASE_URL: {api_base}")
    else:
        print(f"  [INFO] DEEPSEEK_BASE_URL: not configured (will use default)")
    
    if model_extract:
        print(f"  [OK] DEEPSEEK_MODEL_EXTRACT: {model_extract}")
    else:
        print(f"  [INFO] DEEPSEEK_MODEL_EXTRACT: not configured (will use default)")
    
    if model_strategy:
        print(f"  [OK] DEEPSEEK_MODEL_STRATEGY: {model_strategy}")
    else:
        print(f"  [INFO] DEEPSEEK_MODEL_STRATEGY: not configured (will use default)")
    
    # Test API connectivity if configured
    if api_key and api_base:
        print()
        print("--- API Connectivity Test ---")
        try:
            import httpx
            response = httpx.get(
                f"{api_base}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if response.status_code == 200:
                print(f"  [OK] API endpoint reachable")
            else:
                print(f"  [WARN] API endpoint returned status {response.status_code}")
        except Exception as e:
            print(f"  [FAIL] API endpoint unreachable: {e}")
    
    print()
    if all_ok:
        print("All checks passed. V18 is ready.")
        if not api_key:
            print("NOTE: No API configured. Analysis will use local fallback (basic preview only).")
    else:
        print("Some checks failed. Please fix the issues above.")
    
    return all_ok

def cmd_analyze(input_dir: str, identity: str, goal: str, output_dir: str):
    """Run analysis pipeline."""
    from core.fact_card import PipelineContext
    from core.pipeline import run_pipeline
    
    print(f"=== 明证台 V18 Analyze ===")
    print(f"Input: {input_dir}")
    print(f"Identity: {identity}")
    print(f"Goal: {goal}")
    print(f"Output: {output_dir}")
    print()
    
    # Validate inputs
    if not Path(input_dir).exists():
        print(f"ERROR: Input directory does not exist: {input_dir}")
        return False
    
    from core.scenario_router import validate_identity, validate_goal
    if not validate_identity(identity):
        print(f"ERROR: Invalid identity: {identity}")
        return False
    if not validate_goal(goal):
        print(f"ERROR: Invalid goal: {goal}")
        return False
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "customer"), exist_ok=True)
    
    # Create pipeline context
    ctx = PipelineContext(
        input_dir=input_dir,
        output_dir=output_dir,
        identity=identity,
        goal=goal
    )
    
    # Run pipeline
    print("Running analysis pipeline...")
    ctx = run_pipeline(ctx)
    
    # Print results
    print()
    print("=== Pipeline Results ===")
    for log in ctx.logs:
        print(f"  {log}")
    
    if ctx.errors:
        print()
        print("=== Errors ===")
        for err in ctx.errors:
            print(f"  ERROR: {err}")
        return False
    
    print()
    print(f"Analysis complete. Output: {output_dir}")
    return True

def cmd_inspect(case_dir: str):
    """Inspect a case output directory."""
    print(f"=== 明证台 V18 Inspect ===")
    print(f"Case: {case_dir}")
    print()
    
    case_path = Path(case_dir)
    if not case_path.exists():
        print(f"ERROR: Case directory does not exist: {case_dir}")
        return False
    
    customer_dir = case_path / "customer"
    if not customer_dir.exists():
        print("No customer/ directory found.")
        return False
    
    # List files
    print("Files in customer/:")
    for f in sorted(customer_dir.iterdir()):
        size = f.stat().st_size
        print(f"  {f.name} ({size:,} bytes)")
    
    # Check for distilled card (in _internal subfolder)
    distilled_path = case_path / "_internal" / "distilled_card.json"
    if distilled_path.exists():
        import json
        with open(distilled_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print()
        print("Distilled Card Summary:")
        fc = data.get("fact_card", {})
        sc = data.get("strategy_card", {})
        print(f"  Case ID: {fc.get('case_id', 'N/A')}")
        print(f"  Court: {fc.get('court', 'N/A')}")
        print(f"  Identity: {fc.get('identity', 'N/A')}")
        print(f"  Amount: {fc.get('amount', 'N/A')}")
        print(f"  Key Facts: {len(fc.get('key_facts', []))}")
        print(f"  Disputed Facts: {len(fc.get('disputed_facts', []))}")
        print(f"  Missing Materials: {len(fc.get('missing_materials', []))}")
        print(f"  SABCD Rating: {sc.get('sabcd_rating', 'N/A')}")
    
    return True

def cmd_package(case_dir: str):
    """Create delivery package from case directory."""
    print(f"=== 明证台 V18 Package ===")
    print(f"Case: {case_dir}")
    print()
    
    from core.render.zip_builder import build_zip
    
    customer_dir = os.path.join(case_dir, "customer")
    zip_path = os.path.join(customer_dir, "客户交付包.zip")
    
    if build_zip(customer_dir, zip_path):
        print(f"Package created: {zip_path}")
        return True
    else:
        print("Failed to create package")
        return False

def cmd_selfcheck(case_dir: str):
    """Run quality self-check on case output."""
    print(f"=== 明证台 V18 Self-Check ===")
    print(f"Case: {case_dir}")
    print()
    
    customer_dir = os.path.join(case_dir, "customer")
    
    if not os.path.exists(customer_dir):
        print(f"ERROR: Customer directory not found: {customer_dir}")
        return False
    
    from core.quality.final_artifact_auditor import audit_artifacts
    
    report = audit_artifacts(customer_dir)
    
    for check in report.checks:
        status = "[OK]" if check.passed else "[FAIL]"
        print(f"  {status} {check.check_name}: {check.message}")
    
    print()
    print(report.summary())
    
    return report.passed

def main():
    parser = argparse.ArgumentParser(description="明证台 V18 Core Runner")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # doctor
    subparsers.add_parser("doctor", help="Check environment")
    
    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Run analysis")
    analyze_parser.add_argument("--input", required=True, help="Input directory")
    analyze_parser.add_argument("--identity", required=True, help="Identity (投诉方/起诉方/被诉方/行政复议申请人/整理证据)")
    analyze_parser.add_argument("--goal", required=True, help="Goal (投诉举报/起诉立案/应诉答辩/行政复议/申请再审/证据整理)")
    analyze_parser.add_argument("--out", required=True, help="Output directory")
    
    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect case")
    inspect_parser.add_argument("--case", required=True, help="Case directory")
    
    # package
    package_parser = subparsers.add_parser("package", help="Create package")
    package_parser.add_argument("--case", required=True, help="Case directory")
    
    # selfcheck
    selfcheck_parser = subparsers.add_parser("selfcheck", help="Run quality check")
    selfcheck_parser.add_argument("--case", required=True, help="Case directory")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    success = False
    if args.command == "doctor":
        success = cmd_doctor()
    elif args.command == "analyze":
        success = cmd_analyze(args.input, args.identity, args.goal, args.out)
    elif args.command == "inspect":
        success = cmd_inspect(args.case)
    elif args.command == "package":
        success = cmd_package(args.case)
    elif args.command == "selfcheck":
        success = cmd_selfcheck(args.case)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
