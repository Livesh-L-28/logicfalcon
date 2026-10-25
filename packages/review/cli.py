"""Command-line interface for AEGIS AI Code Review."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

from packages.review.domain.models import FindingSeverity, ReviewReport
from packages.review.engine import LocalReviewEngine, ReviewConfig
from packages.review.validator import FindingValidator

try:
    from logicfalcon import __version__
except ImportError:
    __version__ = "0.1.5"

SEVERITY_WEIGHTS: dict[FindingSeverity, int] = {
    FindingSeverity.INFO: 0,
    FindingSeverity.WARNING: 1,
    FindingSeverity.ERROR: 2,
    FindingSeverity.CRITICAL: 3,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logicfalcon review",
        description="LogicFalcon — Repository Intelligence & Automated Code Review CLI (Powered by AEGIS AI)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Path to the repository root directory (default: current directory).",
    )
    parser.add_argument(
        "--base",
        type=str,
        default=None,
        help="Base Git commit or branch reference to compare against (e.g., 'main', 'origin/main').",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "sarif", "markdown", "vscode"],
        default="text",
        help="Output format: human-readable 'text', machine 'json', standard 'sarif', 'markdown', or 'vscode' diagnostics (default: text).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to custom review configuration file (.logicfalcon.json, .logicfalcon.yml).",
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Path to baseline findings JSON file to suppress known existing technical debt.",
    )
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Restrict analysis output strictly to lines changed within the diff.",
    )
    parser.add_argument(
        "--severity-threshold",
        choices=["INFO", "WARNING", "ERROR", "CRITICAL"],
        default="ERROR",
        help="Minimum finding severity that triggers a non-zero exit code (default: ERROR).",
    )
    parser.add_argument(
        "--enable-ai",
        action="store_true",
        help="Enable repository-aware AI analysis in addition to deterministic static rules.",
    )
    parser.add_argument(
        "--enable-tools",
        action="store_true",
        help="Enable external deterministic linters (e.g., Ruff) if installed.",
    )
    parser.add_argument(
        "--staged",
        "--cached",
        action="store_true",
        help="Review staged (cached) Git changes only.",
    )
    parser.add_argument(
        "--unstaged",
        action="store_true",
        help="Review unstaged working tree changes only.",
    )
    parser.add_argument(
        "--show-fixes",
        action="store_true",
        help="Display detailed proposed fixes and code diff previews for findings.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-file analysis timeout in seconds (default: 10.0).",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Analyze a single target file directly instead of a git diff.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read target file content directly from standard input (useful for unsaved editor buffers).",
    )
    parser.add_argument(
        "--workspace",
        action="store_true",
        help="Analyze all supported project files across the workspace.",
    )
    parser.add_argument(
        "--with-re-context",
        action="store_true",
        help="Enrich findings with Reverse Engineering Intelligence (components, reachability, blast radius).",
    )
    parser.add_argument(
        "--with-impact",
        action="store_true",
        help="Enrich review with Change Impact Analysis & Predictive Test Selection.",
    )
    return parser


def format_text_report(report: ReviewReport, changed_only: bool = False, show_fixes: bool = False) -> str:
    lines = [
        "=" * 78,
        "🦅  LogicFalcon — Repository Intelligence & Code Review Report (Powered by AEGIS AI)",
        "=" * 78,
        f"Repository:   {report.repository_path}",
        f"Base Commit:  {report.base_commit or 'HEAD'}",
        f"Head Commit:  {report.head_commit or 'Working Tree'}",
        f"Files Scanned:{len(report.files_reviewed)}",
        f"Total Findings: {len(report.findings)}",
        f"Duration:     {report.execution_time_seconds}s",
        "-" * 78,
    ]

    if report.affected_artifacts.affected_tests:
        lines.append(f"Potentially Affected Tests ({len(report.affected_artifacts.affected_tests)}):")
        for test_file in report.affected_artifacts.affected_tests[:10]:
            lines.append(f"  • {test_file}")
        if len(report.affected_artifacts.affected_tests) > 10:
            lines.append(f"  ... and {len(report.affected_artifacts.affected_tests) - 10} more")
        lines.append("-" * 78)

    if not report.findings:
        lines.append("✅ No quality, reliability, or security findings detected.")
        lines.append("=" * 78)
        return "\n".join(lines)

    lines.append(f"{'SEV':<10} {'LOCATION':<32} {'RULE':<12} {'MESSAGE'}")
    lines.append("-" * 78)

    for f in report.findings:
        loc = f"{f.location.file_path}:{f.location.start_line}"
        if len(loc) > 30:
            loc = "..." + loc[-27:]
        lines.append(f"{f.severity.value:<10} {loc:<32} {f.rule_id:<12} {f.title}")
        if f.technical_evidence:
            lines.append(f"           Evidence: {f.technical_evidence}")
        if f.why_it_matters:
            lines.append(f"           Impact:   {f.why_it_matters}")
        if f.proposed_fix and (show_fixes or f.proposed_fix.replacement_code):
            lines.append(f"           Fix:      {f.proposed_fix.explanation}")
            if f.proposed_fix.replacement_code:
                lines.append(f"           Replace:  {f.proposed_fix.replacement_code}")
        elif f.suggestion:
            lines.append(f"           Fix:      {f.suggestion}")
        lines.append("")

    lines.append("=" * 78)
    return "\n".join(lines)


def format_markdown_report(report: ReviewReport) -> str:
    lines = [
        "## 🦅 LogicFalcon Code Review Summary",
        "",
        f"- **Repository:** `{report.repository_path}`",
        f"- **Base / Head:** `{report.base_commit or 'HEAD'}` ... `{report.head_commit or 'Working Tree'}`",
        f"- **Files Scanned:** {len(report.files_reviewed)}",
        f"- **Total Findings:** {len(report.findings)}",
        f"- **Execution Time:** {report.execution_time_seconds}s",
        "",
    ]
    if report.affected_artifacts.affected_tests:
        lines.append(f"### 🧪 Potentially Impacted Tests ({len(report.affected_artifacts.affected_tests)})")
        for t in report.affected_artifacts.affected_tests[:5]:
            lines.append(f"- `{t}`")
        if len(report.affected_artifacts.affected_tests) > 5:
            lines.append(f"- *... and {len(report.affected_artifacts.affected_tests) - 5} more*")
        lines.append("")

    if not report.findings:
        lines.append("✅ **All quality, security, and reliability checks passed cleanly.**")
        return "\n".join(lines)

    lines.append("### 📋 Review Findings")
    lines.append("| Severity | Location | Rule | Title |")
    lines.append("|:---|:---|:---|:---|")
    for f in report.findings:
        lines.append(f"| **{f.severity.value}** | `{f.location.file_path}:{f.location.start_line}` | `{f.rule_id}` | {f.title} |")
    lines.append("")

    lines.append("### 🔍 Details & Remediation")
    for f in report.findings:
        lines.append(f"#### [{f.severity.value}] {f.title} (`{f.rule_id}`)")
        lines.append(f"**Location:** `{f.location.file_path}:{f.location.start_line}`")
        lines.append(f"\n{f.message}\n")
        if f.technical_evidence:
            lines.append(f"**Evidence:** `{f.technical_evidence}`\n")
        if f.why_it_matters:
            lines.append(f"**Impact:** {f.why_it_matters}\n")
        if f.proposed_fix and f.proposed_fix.replacement_code:
            lines.append("**Proposed Fix:**")
            lines.append(f"```suggestion\n{f.proposed_fix.replacement_code}\n```\n")
        elif f.suggestion:
            lines.append(f"**Suggestion:** {f.suggestion}\n")
        lines.append("---")

    return "\n".join(lines)


def format_sarif_report(report: ReviewReport) -> str:
    rules_map: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    level_map = {
        "INFO": "note",
        "WARNING": "warning",
        "ERROR": "error",
        "CRITICAL": "error",
    }

    for f in report.findings:
        if f.rule_id not in rules_map:
            rules_map[f.rule_id] = {
                "id": f.rule_id,
                "name": f.title,
                "shortDescription": {"text": f.title},
                "fullDescription": {"text": f.message},
                "defaultConfiguration": {"level": level_map.get(f.severity.value, "warning")},
                "properties": {
                    "category": f.category.value,
                    "why_it_matters": f.why_it_matters,
                },
            }

        res_obj: dict[str, Any] = {
            "ruleId": f.rule_id,
            "level": level_map.get(f.severity.value, "warning"),
            "message": {
                "text": f"{f.title}: {f.message}" + (f"\nFix: {f.proposed_fix.explanation}" if f.proposed_fix else ""),
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": f.location.file_path,
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": {
                            "startLine": max(1, f.location.start_line),
                            "endLine": max(1, f.location.end_line or f.location.start_line),
                            "startColumn": f.location.start_column or 1,
                        },
                    }
                }
            ],
            "properties": {
                "confidence": f.confidence,
                "tool_name": f.tool_name,
            },
        }
        if "dependency_path" in f.metadata:
            res_obj["properties"]["dependency_path"] = f.metadata["dependency_path"]
        if "rule_type" in f.metadata:
            res_obj["properties"]["rule_type"] = f.metadata["rule_type"]
        if f.proposed_fix and f.proposed_fix.replacement_code:
            res_obj["fixes"] = [
                {
                    "description": {"text": f.proposed_fix.explanation or "Apply automated fix"},
                    "fileChanges": [
                        {
                            "artifactLocation": {"uri": f.proposed_fix.file_path},
                            "replacements": [
                                {
                                    "deletedRegion": {
                                        "startLine": f.proposed_fix.start_line,
                                        "endLine": f.proposed_fix.end_line,
                                    },
                                    "insertedContent": {"text": f.proposed_fix.replacement_code},
                                }
                            ],
                        }
                    ],
                }
            ]
        results.append(res_obj)

    sarif_doc = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "LogicFalcon",
                        "fullName": "LogicFalcon Code Review Engine (Powered by AEGIS AI)",
                        "version": __version__,
                        "rules": list(rules_map.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif_doc, indent=2)


def format_vscode_report(report: ReviewReport) -> str:
    severity_map = {
        "CRITICAL": "Error",
        "ERROR": "Error",
        "WARNING": "Warning",
        "INFO": "Information",
    }
    diagnostics = [
        {
            "file": f.location.file_path,
            "line": max(1, f.location.start_line),
            "column": f.location.start_column or 1,
            "endLine": max(1, f.location.end_line or f.location.start_line),
            "endColumn": (f.location.start_column or 1) + 1,
            "severity": severity_map.get(f.severity.value, "Information"),
            "message": f.message,
            "code": f.rule_id,
            "source": "LogicFalcon",
            "suggestion": f.suggestion or (f.proposed_fix.replacement_code if f.proposed_fix else None),
        }
        for f in report.findings
    ]
    return json.dumps(diagnostics, indent=2)


def run_cli(args: list[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args)

    repo_path = Path(parsed.repo).resolve()
    if not repo_path.exists():
        sys.stderr.write(f"Error: Repository path '{repo_path}' does not exist.\n")
        return 2

    # Load configuration from file or defaults
    try:
        config = ReviewConfig.load_config(
            config_path=parsed.config,
            repo_root=repo_path,
            raise_on_error=bool(parsed.config),
        )
    except Exception as e:
        sys.stderr.write(f"Configuration error: {e}\n")
        return 2

    if parsed.timeout:
        config.per_file_timeout_seconds = parsed.timeout
    if parsed.enable_tools:
        config.enable_external_tools = True
    if parsed.enable_ai:
        config.enable_ai_review = True
    if getattr(parsed, "with_re_context", False):
        config.include_re_context = True
    if getattr(parsed, "with_impact", False):
        config.include_impact_analysis = True

    engine = LocalReviewEngine(repo_root=repo_path, config=config)

    try:
        if parsed.file:
            stdin_content: str | None = None
            if parsed.stdin:
                stdin_content = sys.stdin.read()
            report = engine.review_file(parsed.file, content=stdin_content)
        elif parsed.workspace:
            discovered_files: list[str] = []
            max_workspace_files = 1000
            for ext in (".py", ".ts", ".js", ".tsx", ".jsx"):
                for p in repo_path.rglob(f"*{ext}"):
                    if p.is_file():
                        try:
                            rel = str(p.relative_to(repo_path))
                            if not engine._is_ignored(rel):
                                discovered_files.append(rel)
                                if len(discovered_files) >= max_workspace_files:
                                    break
                        except ValueError:
                            continue
                if len(discovered_files) >= max_workspace_files:
                    break
            report = engine.review_files(discovered_files)
        else:
            report = engine.review_local_git_diff(
                base_ref=parsed.base,
                staged=parsed.staged,
                unstaged=parsed.unstaged,
            )
            # Validate findings and suppress hallucinations/invalid locations for diff reviews
            validator = FindingValidator(repo_root=repo_path)
            verified_findings, _ = validator.validate(report.findings)
            report.findings = verified_findings
    except Exception as e:
        sys.stderr.write(f"Review execution failure: {e}\n")
        return 2

    # Optional baseline debt suppression
    if parsed.baseline:
        baseline_file = Path(parsed.baseline) if Path(parsed.baseline).is_absolute() else repo_path / parsed.baseline
        if baseline_file.is_file():
            try:
                base_data = json.loads(baseline_file.read_text(encoding="utf-8"))
                base_findings = base_data.get("findings", [])
                base_hashes = {
                    bf.get("deduplication_hash") or f"{bf.get('location', {}).get('file_path')}:{bf.get('location', {}).get('start_line')}:{bf.get('rule_id')}"
                    for bf in base_findings
                }
                orig_count = len(report.findings)
                report.findings = [f for f in report.findings if f.deduplication_hash not in base_hashes]
                suppressed = orig_count - len(report.findings)
                if suppressed > 0:
                    report.errors.append(f"Baseline suppression: {suppressed} known existing finding(s) filtered.")
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to parse baseline file '{parsed.baseline}': {e}\n")

    if parsed.format == "json":
        sys.stdout.write(report.model_dump_json(indent=2) + "\n")
    elif parsed.format == "sarif":
        sys.stdout.write(format_sarif_report(report) + "\n")
    elif parsed.format == "markdown":
        sys.stdout.write(format_markdown_report(report) + "\n")
    elif parsed.format == "vscode":
        sys.stdout.write(format_vscode_report(report) + "\n")
    else:
        sys.stdout.write(format_text_report(report, changed_only=parsed.changed_only, show_fixes=parsed.show_fixes) + "\n")

    # Evaluate exit code against severity threshold
    threshold_weight = SEVERITY_WEIGHTS[FindingSeverity(parsed.severity_threshold)]
    has_blocking_violations = any(
        SEVERITY_WEIGHTS[f.severity] >= threshold_weight for f in report.findings
    )

    return 1 if has_blocking_violations else 0


def main() -> NoReturn:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
