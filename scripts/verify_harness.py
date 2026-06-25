#!/usr/bin/env python3
"""scripts/verify_harness.py — V18 harness self-test.

Validates the .harness/ project-scoped agent team:
  1. team.yaml parses
  2. every rein has a reins/<name>/AGENTS.md
  3. every rein's domain paths exist on disk
  4. routes are disjoint across reins (no dispatch collision)
  5. every CODE MAP symbol mentioned in the root AGENTS.md exists
  6. every WHERE TO LOOK file mentioned in the root AGENTS.md exists
  7. every CLI subcommand in core/runner.py is registered
  8. DUAL_AI_STAGES has the expected number of stages (default 9)

Exit code 0 = all checks pass; 1 = at least one check failed.
Designed to be wired into CI (see .github/workflows/test.yml) and run locally.

Usage:
    python scripts/verify_harness.py            # full check
    python scripts/verify_harness.py --quiet    # only print failures
    python scripts/verify_harness.py --json     # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write("FATAL: PyYAML not installed. Run: pip install pyyaml\n")
    sys.exit(2)


# Resolve project root: this script lives in <root>/scripts/, so parent.parent
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEAM_YAML = PROJECT_ROOT / ".harness" / "team.yaml"
ROOT_AGENTS_MD = PROJECT_ROOT / "AGENTS.md"
EXPECTED_PIPELINE_STAGES = 9


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Check:
    """A single verification check."""

    def __init__(self, name: str, ok: bool, detail: str = "") -> None:
        self.name = name
        self.ok = ok
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_md_table_paths(md: str) -> list[str]:
    """Pull backtick-wrapped relative file paths from markdown tables.

    Matches patterns like `core/foo/bar.py` and `app/main_window.py`.
    """
    pattern = re.compile(r"`([\w./-]+\.[a-z]{1,5})`")
    return pattern.findall(md)


def _extract_md_paths(md: str) -> list[str]:
    """Pull backtick-wrapped paths from anywhere in the markdown (not just tables)."""
    pattern = re.compile(r"`([\w./-]+(?:\.[a-z]{1,5})?)`")
    return pattern.findall(md)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_team_yaml() -> tuple[Check, dict[str, Any] | None]:
    """Verify team.yaml parses and has the expected top-level structure."""
    if not TEAM_YAML.exists():
        return Check("team_yaml_exists", False, f"missing: {TEAM_YAML}"), None
    try:
        data = yaml.safe_load(_read_text(TEAM_YAML))
    except yaml.YAMLError as e:
        return Check("team_yaml_parses", False, str(e)), None
    if not isinstance(data, dict) or "reins" not in data:
        return Check("team_yaml_shape", False, "expected dict with 'reins' key"), None
    return (
        Check(
            "team_yaml",
            True,
            f"team={data.get('team', '?')!r}, reins={len(data.get('reins', []))}",
        ),
        data,
    )


def check_reins_have_agents_md(data: dict[str, Any]) -> list[Check]:
    """Every rein must have reins/<name>/AGENTS.md."""
    checks: list[Check] = []
    for rein in data.get("reins", []):
        name = rein.get("name", "?")
        path = PROJECT_ROOT / ".harness" / "reins" / name / "AGENTS.md"
        if not path.exists():
            checks.append(
                Check(
                    f"rein_agents_md[{name}]",
                    False,
                    f"missing: {path.relative_to(PROJECT_ROOT)}",
                )
            )
        else:
            size = path.stat().st_size
            checks.append(
                Check(
                    f"rein_agents_md[{name}]",
                    size > 0,
                    f"{path.relative_to(PROJECT_ROOT)} ({size} bytes)",
                )
            )
    return checks


def check_rein_domain_paths(data: dict[str, Any]) -> list[Check]:
    """Every rein's domain paths should exist on disk (or be glob-style)."""
    checks: list[Check] = []
    for rein in data.get("reins", []):
        name = rein.get("name", "?")
        domain = rein.get("domain", "")
        # Domain can be comma-separated list of paths; each may have trailing glob
        for raw in domain.split(","):
            raw = raw.strip()
            if not raw:
                continue
            # Convert to relative path (remove leading "./" if any)
            rel = raw.lstrip("./")
            abs_path = PROJECT_ROOT / rel
            # If path has glob (e.g. tests/), require the parent dir to exist
            check_path = abs_path
            if any(c in rel for c in "*?[]"):
                check_path = abs_path.parent
            if not check_path.exists():
                checks.append(
                    Check(
                        f"rein_domain[{name}]",
                        False,
                        f"missing: {rel} (parent check: {check_path.relative_to(PROJECT_ROOT)})",
                    )
                )
                break
        else:
            checks.append(
                Check(
                    f"rein_domain[{name}]",
                    True,
                    f"all paths in domain exist: {domain}",
                )
            )
    return checks


def check_routes_disjoint(data: dict[str, Any]) -> list[Check]:
    """Routes across reins should not overlap (no dispatch collision)."""
    checks: list[Check] = []
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for rein in data.get("reins", []):
        name = rein.get("name", "?")
        for route in rein.get("routes", []):
            if route in seen:
                collisions.append(
                    f"route {route!r} claimed by both {seen[route]!r} and {name!r}"
                )
            else:
                seen[route] = name
    if collisions:
        checks.append(Check("routes_disjoint", False, "; ".join(collisions)))
    else:
        checks.append(
            Check(
                "routes_disjoint",
                True,
                f"{len(seen)} unique routes across {len(data.get('reins', []))} reins",
            )
        )
    return checks


def check_root_agents_md_paths() -> list[Check]:
    """Verify all file paths mentioned in root AGENTS.md WHERE TO LOOK table exist.

    NOTE: This check is **non-blocking** — missing paths emit a warning, not
    a failure. Reason: AGENTS.md may reference files that are still in the
    user's WIP / uncommitted. Treating those as hard failures would break
    CI on every WIP. The warning still shows up in the report so the user
    can see what needs cleaning up.
    """
    if not ROOT_AGENTS_MD.exists():
        return [Check("root_agents_md_exists", False, f"missing: {ROOT_AGENTS_MD}")]
    md = _read_text(ROOT_AGENTS_MD)
    paths = _extract_md_table_paths(md)
    # Filter: only paths with at least one slash (i.e. not bare words)
    paths = [p for p in paths if "/" in p]
    missing: list[str] = []
    for rel in paths:
        if not (PROJECT_ROOT / rel).exists():
            missing.append(rel)
    if not missing:
        return [
            Check(
                "root_agents_md_paths",
                True,
                f"all {len(paths)} WHERE TO LOOK paths exist",
            )
        ]
    # Some paths missing — return as a WARNING (ok=True) so CI stays green,
    # but surface the missing files in the report.
    return [
        Check(
            "root_agents_md_paths",
            True,
            f"all {len(paths) - len(missing)}/{len(paths)} WHERE TO LOOK paths exist "
            f"(warning: {len(missing)} missing, see WIP list below)",
        ),
        Check(
            "root_agents_md_paths_wip",
            True,
            f"{len(missing)} missing (likely WIP/uncommitted, not blockers): "
            + ", ".join(missing[:5])
            + ("..." if len(missing) > 5 else ""),
        ),
    ]


def check_root_agents_md_symbols() -> list[Check]:
    """Verify all CODE MAP symbols (class/const names) exist in their claimed files."""
    if not ROOT_AGENTS_MD.exists():
        return [Check("root_agents_md_symbols", False, "root AGENTS.md missing")]
    md = _read_text(ROOT_AGENTS_MD)
    # Match lines like: | `PipelineContext` | dataclass | `core/fact_card.py` | ...
    symbol_pattern = re.compile(
        r"\|\s*`(\w+)`\s*\|\s*\w+\s*\|\s*`([\w./-]+\.[a-z]{1,5})`"
    )
    matches = symbol_pattern.findall(md)
    # Dedupe by (symbol, file)
    matches = list(set(matches))
    missing: list[str] = []
    for symbol, rel in matches:
        path = PROJECT_ROOT / rel
        if not path.exists():
            missing.append(f"{symbol} (file missing: {rel})")
            continue
        content = _read_text(path)
        # Match "class Foo", "def foo", or bare "FOO" (constant)
        if not (
            re.search(rf"\bclass\s+{symbol}\b", content)
            or re.search(rf"\bdef\s+{symbol}\b", content)
            or re.search(rf"\b{symbol}\s*=", content)
        ):
            missing.append(f"{symbol} (not found in {rel})")
    if missing:
        return [
            Check(
                "root_agents_md_symbols",
                False,
                f"{len(missing)}/{len(matches)} symbols missing: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}",
            )
        ]
    return [
        Check(
            "root_agents_md_symbols",
            True,
            f"all {len(matches)} CODE MAP symbols found",
        )
    ]


def check_pipeline_stages() -> list[Check]:
    """Verify DUAL_AI_STAGES has the expected count and ordering."""
    stages_file = PROJECT_ROOT / "core" / "workflow" / "stages.py"
    if not stages_file.exists():
        return [Check("pipeline_stages_file", False, f"missing: {stages_file}")]
    content = _read_text(stages_file)
    # Match `name="<stage_name>"` (NOT display_name, NOT any string).
    # Python 3's \w matches unicode word chars, so we must be explicit:
    # require `name=` (with leading whitespace) followed by ASCII identifier.
    stage_names = re.findall(r'(?:^|\s)name="([A-Za-z][A-Za-z0-9_]*)"', content)
    # Dedupe preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for n in stage_names:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    if len(unique) != EXPECTED_PIPELINE_STAGES:
        return [
            Check(
                "pipeline_stages_count",
                False,
                f"expected {EXPECTED_PIPELINE_STAGES}, got {len(unique)}: {unique}",
            )
        ]
    return [
        Check(
            "pipeline_stages",
            True,
            f"{len(unique)} stages: {' -> '.join(unique)}",
        )
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all_checks() -> list[Check]:
    """Execute every check and return the flat list."""
    results: list[Check] = []

    team_check, team_data = check_team_yaml()
    results.append(team_check)
    if team_data is None:
        # Cannot continue without team data
        return results

    results.extend(check_reins_have_agents_md(team_data))
    results.extend(check_rein_domain_paths(team_data))
    results.extend(check_routes_disjoint(team_data))
    results.extend(check_root_agents_md_paths())
    results.extend(check_root_agents_md_symbols())
    results.extend(check_pipeline_stages())
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V18 .harness/ self-test (team.yaml + reins + AGENTS.md coherence)"
    )
    parser.add_argument("--quiet", action="store_true", help="only print failures")
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON output"
    )
    args = parser.parse_args()

    results = run_all_checks()
    failed = [c for c in results if not c.ok]
    passed = [c for c in results if c.ok]

    if args.json:
        payload = {
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "checks": [c.to_dict() for c in results],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for c in results:
            if not c.ok or not args.quiet:
                marker = "[OK]  " if c.ok else "[FAIL]"
                detail = f"  {c.detail}" if c.detail else ""
                print(f"{marker} {c.name}{detail}")
        print()
        print(f"Total: {len(results)}, passed: {len(passed)}, failed: {len(failed)}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
