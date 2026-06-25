"""scripts/scan_repo.py — V18 one-shot repo scan for hygiene gaps.

Used during init bootstrap to identify what's missing or weak. Not part of
production. Run with: python scripts/scan_repo.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def header(s: str) -> None:
    print()
    print(f"=== {s} ===")


def scan_docs() -> list[tuple[str, str]]:
    header("docs (README / LICENSE / CHANGELOG)")
    expected = [
        ("README.md", "project intro"),
        ("LICENSE", "license file"),
        ("CHANGELOG.md", "release notes"),
        ("CONTRIBUTING.md", "contribution guide"),
        ("SECURITY.md", "security policy"),
        (".github/CODEOWNERS", "code ownership"),
        (".github/ISSUE_TEMPLATE/bug_report.md", "bug report template"),
    ]
    found: list[tuple[str, str]] = []
    for rel, desc in expected:
        p = ROOT / rel
        marker = "FOUND" if p.exists() else "MISSING"
        if p.exists():
            found.append((rel, desc))
        print(f"  [{marker:7s}] {rel:40s} ({desc})")
    return found


def scan_secrets() -> dict[str, int]:
    header("secrets (hardcoded in .py files)")
    patterns = [
        ("MiniMax sk- key", r"sk-[a-zA-Z0-9_-]{20,}"),
        ("MiMo tp- key", r"tp-cn-[a-zA-Z0-9]{10,}"),
        ("API key = literal", r"""api[_-]?key\s*[:=]\s*['"][^'\"]{16,}"""),
        ("token = literal", r"""token\s*[:=]\s*['"][^'\"]{16,}"""),
        ("password = literal", r"""password\s*[:=]\s*['"][^'\"]{8,}"""),
        ("Authorization Bearer", r"Authorization:\s*Bearer\s+[A-Za-z0-9_-]{16,}"),
    ]
    hits: dict[str, int] = {}
    for py in ROOT.rglob("*.py"):
        # Skip test files and venv
        rel = py.relative_to(ROOT)
        if "tests" in rel.parts or "_legacy_root" in rel.parts or ".venv" in rel.parts:
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name, pat in patterns:
            for m in re.finditer(pat, text):
                # Get line number
                line_no = text[: m.start()].count("\n") + 1
                # Get the actual matched line
                line = text.split("\n")[line_no - 1].strip()
                # Filter out env-var reads and obvious non-secrets
                if any(
                    kw in line.lower()
                    for kw in [
                        "os.environ",
                        "os.getenv",
                        "os.environ.get",
                        "config.get",
                        "settings.",
                        "settings_",
                        "_config",
                        "PLACEHOLDER",
                        "example",
                        "test_",
                        "fake",
                        "xxx",
                        "<your",
                        "your-",
                    ]
                ):
                    continue
                hits[name] = hits.get(name, 0) + 1
                if hits[name] <= 2:
                    print(f"  [{name}] {rel}:{line_no}")
                    print(f"    {line[:120]}")
    if not hits:
        print("  [clean] no hardcoded secrets found in core/ or app/")
    return hits


def scan_env_files() -> None:
    header("env files in repo")
    found = False
    for p in ROOT.rglob(".env*"):
        rel = p.relative_to(ROOT)
        # Skip .env in .gitignore (it's the user's own .env which is fine)
        if p.name in (".env", ".env.example", ".env.local", ".env.production"):
            marker = "WARN" if p.name == ".env" else "INFO"
            print(f"  [{marker}] {rel}")
            found = True
    if not found:
        print("  [clean] no .env files in repo")


def scan_dependencies() -> None:
    header("dependency manifests")
    expected = ["requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile"]
    for rel in expected:
        p = ROOT / rel
        if p.exists():
            size = p.stat().st_size
            print(f"  [FOUND  ] {rel} ({size} bytes)")
        else:
            print(f"  [MISSING] {rel}")


def scan_ci() -> None:
    header("CI configuration")
    candidates = [
        ".github/workflows",
        ".gitlab-ci.yml",
        "azure-pipelines.yml",
        ".circleci",
        "Jenkinsfile",
        ".buildkite",
    ]
    any_found = False
    for rel in candidates:
        p = ROOT / rel
        if p.exists():
            any_found = True
            if p.is_dir():
                files = list(p.glob("*.yml")) + list(p.glob("*.yaml"))
                print(f"  [FOUND] {rel}/ ({len(files)} workflow files)")
                for f in files:
                    print(f"          - {f.name}")
            else:
                print(f"  [FOUND] {rel}")
    if not any_found:
        print("  [MISSING] no CI config found")


def scan_prints_in_core() -> int:
    header("print() calls in core/ (vs logger)")
    n = 0
    by_file: dict[str, int] = {}
    for py in (ROOT / "core").rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.split("\n"), 1):
            if re.match(r"^\s*print\(", line) and not line.strip().startswith("#"):
                n += 1
                by_file[str(py.relative_to(ROOT))] = (
                    by_file.get(str(py.relative_to(ROOT)), 0) + 1
                )
    # Top 10 worst offenders
    for f, c in sorted(by_file.items(), key=lambda x: -x[1])[:10]:
        print(f"  {f:50s} {c:3d} prints")
    print(f"  total: {n} print() calls across {len(by_file)} files")
    return n


def main() -> int:
    print(f"Scanning {ROOT}")
    docs_found = scan_docs()
    secrets = scan_secrets()
    scan_env_files()
    scan_dependencies()
    scan_ci()
    n_prints = scan_prints_in_core()

    header("summary")
    print(f"  docs found:     {len(docs_found)}")
    print(f"  secret hits:    {sum(secrets.values())}")
    print(f"  print() in core: {n_prints}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
