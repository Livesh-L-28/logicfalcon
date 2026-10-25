"""Unified Command-Line Interface for LogicFalcon (Powered by AEGIS AI)."""

import argparse
import shutil
import sys
from typing import NoReturn

from logicfalcon import __platform__, __product__, __version__
from packages.intelligence.code.indexer import PythonASTParser
from packages.intelligence.code.ts_parser import JavaScriptTypeScriptParser
from packages.review.cli import run_cli as run_review_cli


def run_doctor(format_json: bool = False) -> int:
    """Runs a non-destructive environment and capability diagnostic."""
    import json

    py_ver = sys.version_info
    py_ok = py_ver >= (3, 12)
    git_bin = shutil.which("git")

    try:
        symbols, _deps = PythonASTParser.parse_source("test.py", "def hello(): pass")
        ast_ok = len(symbols) == 1 and symbols[0].name == "hello"
    except Exception:
        ast_ok = False

    try:
        ts_res = JavaScriptTypeScriptParser().parse_source("test.ts", "function greet(): string { return 'hi'; }")
        ts_ok = len(ts_res.symbols) == 1 and ts_res.symbols[0].name == "greet"
    except Exception:
        ts_ok = False

    ruff_bin = shutil.which("ruff")

    if format_json:
        payload = {
            "product": __product__,
            "version": __version__,
            "platform": __platform__,
            "python_version": f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}",
            "python_meets_requirement": py_ok,
            "git_available": bool(git_bin),
            "git_executable": git_bin,
            "ast_analyzer_available": ast_ok,
            "ts_parser_available": ts_ok,
            "ruff_available": bool(ruff_bin),
            "ruff_executable": ruff_bin,
            "capabilities": [
                "review_diff",
                "review_file",
                "review_workspace",
                "apply_fix",
                "verify_fix",
                "analyze_architecture",
                "reverse_engineer",
            ],

        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 0

    sys.stdout.write(f"🦅  {__product__} — System Diagnostic & Capability Doctor (Powered by {__platform__})\n")
    sys.stdout.write("=" * 65 + "\n")

    # 1. Python version check
    py_status = "PASS" if py_ok else "FAIL"
    sys.stdout.write(f"[{py_status}] Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro} (>= 3.12 required)\n")

    # 2. Git binary check
    git_status = "PASS" if git_bin else "WARN"
    sys.stdout.write(f"[{git_status}] Git Executable: {git_bin or 'Not found in PATH'}\n")

    # 3. Python AST parser check
    ast_status = "PASS" if ast_ok else "FAIL"
    sys.stdout.write(f"[{ast_status}] Python AST Static Analyzer: functional\n")

    # 4. Multi-language TypeScript parser check
    ts_status = "PASS" if ts_ok else "FAIL"
    sys.stdout.write(f"[{ts_status}] TypeScript/JavaScript Static Parser: functional\n")

    # 5. External linter (Ruff) check
    ruff_status = "PASS" if ruff_bin else "INFO"
    sys.stdout.write(f"[{ruff_status}] External Linter (Ruff): {ruff_bin or 'Optional / Not installed'}\n")

    # 6. Service infrastructure status (informational)
    sys.stdout.write("[INFO] Backend Services (PostgreSQL / Redis): Optional (not required for CLI review)\n")
    sys.stdout.write("=" * 65 + "\n")
    sys.stdout.write(f"System diagnostics complete. {__product__} CLI is operational.\n")
    return 0


def run_apply_fix(args: list[str]) -> int:
    """CLI handler for applying fixes safely."""
    import json
    from pathlib import Path

    from logicfalcon.sdk import apply_fix
    from packages.review.domain.models import ProposedFix

    fix_parser = argparse.ArgumentParser(
        prog="logicfalcon apply-fix",
        description="Safely apply a proposed remediation fix with syntax checks and backups.",
    )
    fix_parser.add_argument("--fix", type=str, required=True, help="JSON string or file path to ProposedFix.")
    fix_parser.add_argument("--approved", action="store_true", help="Explicit developer confirmation.")
    fix_parser.add_argument("--dry-run", action="store_true", help="Return diff preview without modifying disk.")
    fix_parser.add_argument("--repo", type=str, default=".", help="Target repository root.")

    parsed = fix_parser.parse_args(args)

    raw_json = parsed.fix
    fix_path = Path(parsed.fix)
    if fix_path.is_file():
        try:
            raw_json = fix_path.read_text(encoding="utf-8")
        except OSError as e:
            sys.stderr.write(json.dumps({"success": False, "error_message": f"Cannot read fix file: {e}"}) + "\n")
            return 2

    try:
        data = json.loads(raw_json)
        fix_obj = ProposedFix.model_validate(data)
    except Exception as e:
        sys.stderr.write(json.dumps({"success": False, "error_message": f"Invalid fix payload: {e}"}) + "\n")
        return 2

    try:
        result = apply_fix(
            fix=fix_obj,
            approved=parsed.approved,
            repo_root=parsed.repo,
            dry_run=parsed.dry_run,
        )
        res_data = {
            "success": result.success,
            "file_path": result.file_path,
            "diff": result.diff,
            "error_message": result.error_message,
            "backup_path": result.backup_path,
            "applied_lines_range": list(result.applied_lines_range),
        }
        sys.stdout.write(json.dumps(res_data, indent=2) + "\n")
        return 0 if result.success else 1
    except Exception as e:
        sys.stderr.write(json.dumps({"success": False, "error_message": str(e)}) + "\n")
        return 1


def build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logicfalcon",
        description=f"{__product__} — Fast, precise engineering intelligence. Powered by {__platform__}.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"{__product__} {__version__} (powered by {__platform__})",
        help="Show program's version number and exit.",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Subcommand: review
    subparsers.add_parser(
        "review",
        help="Run deterministic repository intelligence & automated code review.",
        add_help=False,  # Let review parser handle its own flags
    )

    # Subcommand: doctor
    doc_parser = subparsers.add_parser(
        "doctor",
        help="Run environment health check, AST parser capabilities, and tool diagnostic.",
    )
    doc_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' or 'json' (default: text).",
    )

    # Subcommand: capabilities
    subparsers.add_parser(
        "capabilities",
        help="Query engine capabilities and status in structured JSON format.",
    )

    # Subcommand: architecture
    arch_parser = subparsers.add_parser(
        "architecture",
        help="Inspect repository modularity, dependency cycles, and architectural boundaries.",
    )
    arch_parser.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    arch_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    arch_parser.add_argument("--max-cycles", type=int, default=10, help="Maximum number of cycles to report.")

    # Subcommand: apply-fix
    subparsers.add_parser(
        "apply-fix",
        help="Safely apply a proposed remediation fix with syntax checks and backups.",
        add_help=False,
    )

    # Subcommand: mcp
    subparsers.add_parser(
        "mcp",
        help="Start the Model Context Protocol (MCP) stdio server for AI-first editors.",
    )

    # Subcommand: reverse-engineer
    rev_parser = subparsers.add_parser(
        "reverse-engineer",
        help="Reconstruct repository inventory, architecture, APIs, data models, and call graphs.",
    )
    rev_parser.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    rev_parser.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Output format (default: markdown).")
    rev_parser.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")
    rev_parser.add_argument("--output-dir", type=str, default=None, help="Directory to save generated report.")
    rev_parser.add_argument("--max-file-size", type=int, default=1_000_000, help="Maximum file size in bytes to inspect (default: 1,000,000).")
    rev_parser.add_argument("--max-depth", type=int, default=15, help="Maximum directory depth to traverse (default: 15).")
    rev_parser.add_argument("--timeout", type=float, default=60.0, help="Maximum analysis timeout in seconds (default: 60.0).")
    rev_parser.add_argument("--with-review", action="store_true", help="Run integrated code review alongside reverse engineering.")

    # Subcommand: impact
    imp_parser = subparsers.add_parser(
        "impact",
        help="Predictive change impact intelligence, blast-radius analysis, and test selection.",
    )
    imp_parser.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    imp_parser.add_argument("--base", type=str, default=None, help="Base Git commit or branch to compare against.")
    imp_parser.add_argument("--target", type=str, default="HEAD", help="Target Git revision (default: HEAD).")
    imp_parser.add_argument("--staged", action="store_true", help="Analyze staged Git changes.")
    imp_parser.add_argument("--unstaged", action="store_true", help="Analyze unstaged working tree changes.")
    imp_parser.add_argument("--files", type=str, default=None, help="Comma-separated list of changed file paths.")
    imp_parser.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Report format (default: markdown).")
    imp_parser.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")
    imp_parser.add_argument("--max-depth", type=int, default=5, help="Maximum propagation depth (default: 5).")
    imp_parser.add_argument("--max-entities", type=int, default=500, help="Maximum entity limit (default: 500).")
    imp_parser.add_argument("--conservative-tests", action="store_true", help="Include all repository tests in fallback mode.")
    imp_parser.add_argument("--with-review", action="store_true", help="Execute integrated code review alongside change impact.")
    imp_parser.add_argument("--fail-on-risk", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=None, help="Exit with code 1 if risk meets or exceeds threshold.")

    # Subcommand: history
    subparsers.add_parser(
        "history",
        help="Revision-aware engineering intelligence, historical repository health, and regression analytics.",
        add_help=False,
    )

    # Subcommand: unified
    uni_parser = subparsers.add_parser(
        "unified",
        help="Execute unified engineering intelligence pass synthesizing all analysis pillars.",
    )
    uni_parser.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    uni_parser.add_argument("--staged", action="store_true", help="Analyze staged Git changes.")
    uni_parser.add_argument("--unstaged", action="store_true", help="Analyze unstaged working tree changes.")
    uni_parser.add_argument("--base", type=str, default=None, help="Base Git commit or branch to compare against.")
    uni_parser.add_argument("--target", type=str, default=None, help="Target Git revision.")
    uni_parser.add_argument("--files", type=str, default=None, help="Comma-separated list of target files.")
    uni_parser.add_argument("--save-history", action="store_true", help="Persist snapshot to historical database.")
    uni_parser.add_argument("--db", type=str, default=None, help="Path to SQLite history database.")
    uni_parser.add_argument("--policy-config", type=str, default=None, help="Path to engineering policy gate config JSON.")
    uni_parser.add_argument("--format", choices=["markdown", "json", "text"], default="text", help="Output format (default: text).")
    uni_parser.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")
    uni_parser.add_argument("--fail-on-policy", action="store_true", help="Exit code 1 if engineering policy gate fails.")

    # Subcommand: fde
    subparsers.add_parser(
        "fde",
        help="Forward Deployment Engineering (FDE) discovery, preflight, missions, and runbooks.",
        add_help=False,
    )

    # Subcommand: extension
    subparsers.add_parser(
        "extension",
        help="Discover, install, configure, monitor, update, and manage extensions.",
        add_help=False,
    )
    subparsers.add_parser(
        "extensions",
        help="Alias for extension.",
        add_help=False,
    )

    return parser



def run_architecture(args: list[str]) -> int:
    """CLI handler for architecture and modularity analysis."""
    import argparse
    from pathlib import Path

    from packages.review.analyzer.architecture import ArchitectureAnalyzer

    arch_parser = argparse.ArgumentParser(
        prog="logicfalcon architecture",
        description="Inspect repository modularity, dependency cycles, and architectural boundaries.",
    )
    arch_parser.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    arch_parser.add_argument("--config", type=str, default=None, help="Path to custom config file.")
    arch_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    arch_parser.add_argument("--max-cycles", type=int, default=10, help="Maximum number of cycles to report.")
    arch_parser.add_argument("--show-paths", action="store_true", help="Display full transitive dependency paths for boundary violations.")
    parsed = arch_parser.parse_args(args)

    repo_path = Path(parsed.repo).resolve()
    from packages.review.engine import ReviewConfig
    try:
        config = ReviewConfig.load_config(
            config_path=parsed.config,
            repo_root=repo_path,
            raise_on_error=bool(parsed.config),
        )
    except Exception as e:
        sys.stderr.write(f"Configuration error: {e}\n")
        return 2

    boundary_rules = [r.model_dump() for r in config.architecture_boundaries] if config.architecture_boundaries else None
    effective_policy = config.get_effective_policy()
    analyzer = ArchitectureAnalyzer(
        repo_root=repo_path,
        boundary_rules=boundary_rules,
        policy=effective_policy,
    )
    report = analyzer.analyze()

    if parsed.format == "json":
        sys.stdout.write(report.model_dump_json(indent=2) + "\n")
    else:
        sys.stdout.write(f"🏛️  Architecture & Modularity Report — {__product__}\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Health Score: {report.health_score}/100.0\n")
        sys.stdout.write(f"Summary: {report.health_summary}\n")
        sys.stdout.write(f"Total Python Modules: {report.total_modules}\n")
        sys.stdout.write(f"Total Internal Dependencies: {report.total_internal_dependencies}\n")
        sys.stdout.write(f"Circular Dependency Cycles: {len(report.cycles)}\n")
        for idx, cycle in enumerate(report.cycles[:parsed.max_cycles], 1):
            sys.stdout.write(f"  [{idx}] {cycle.display_path}\n")
        if report.cycle_groups:
            sys.stdout.write(f"Cycle Groups (SCCs): {len(report.cycle_groups)}\n")
            for idx, cg in enumerate(report.cycle_groups[:parsed.max_cycles], 1):
                sys.stdout.write(f"  [{idx}] {cg.id}: {cg.size} modules ({', '.join(cg.modules[:5])}{'...' if len(cg.modules) > 5 else ''})\n")
        sys.stdout.write(f"Boundary Violations: {len(report.boundary_violations)}\n")
        for idx, bv in enumerate(report.boundary_violations, 1):
            if parsed.show_paths and bv.dependency_path:
                path_str = " -> ".join(bv.dependency_path)
                sys.stdout.write(f"  [{idx}] {path_str} ({bv.rule_name})\n")
            else:
                sys.stdout.write(f"  [{idx}] {bv.source_module} -> {bv.target_module} ({bv.rule_name})\n")
        sys.stdout.write("=" * 60 + "\n")

    return 1 if report.cycles or report.boundary_violations else 0


def run_reverse_engineer(args: list[str]) -> int:
    """CLI handler for reverse engineering intelligence."""
    import argparse
    from pathlib import Path

    from packages.review.reverse_engineering.engine import ReverseEngineeringEngine
    from packages.review.reverse_engineering.report_generator import (
        ReverseEngineeringReportGenerator,
    )

    parser = argparse.ArgumentParser(
        prog="logicfalcon reverse-engineer",
        description="Safe, static reverse engineering: inventories, architecture, APIs, data models, call graphs.",
    )
    parser.add_argument("--repo", type=str, default=".", help="Path to repository root (default: current directory).")
    parser.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Report format (default: markdown).")
    parser.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save generated report.")
    parser.add_argument("--max-file-size", type=int, default=1_000_000, help="Maximum file size in bytes to inspect (default: 1,000,000).")
    parser.add_argument("--max-depth", type=int, default=15, help="Maximum directory depth to traverse (default: 15).")
    parser.add_argument("--timeout", type=float, default=60.0, help="Maximum analysis timeout in seconds (default: 60.0).")
    parser.add_argument("--with-review", action="store_true", help="Run integrated code review alongside reverse engineering.")

    try:
        parsed = parser.parse_args(args)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    repo_path = Path(parsed.repo).resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        sys.stderr.write(f"Error: Repository path '{parsed.repo}' does not exist or is not a directory.\n")
        return 2

    engine = ReverseEngineeringEngine(
        repo_root=repo_path,
        max_file_size_bytes=parsed.max_file_size,
        max_depth=parsed.max_depth,
        timeout_seconds=parsed.timeout,
    )

    try:
        if parsed.with_review:
            report = engine.analyze_with_review(run_review=True)
        else:
            report = engine.analyze()

        generator = ReverseEngineeringReportGenerator(report)
        rendered = generator.write_output(
            output_format=parsed.format,
            output_file=parsed.output_file,
            output_dir=parsed.output_dir,
            repo_root=repo_path,
        )
        if not parsed.output_file and not parsed.output_dir:
            sys.stdout.write(rendered)
            if not rendered.endswith("\n"):
                sys.stdout.write("\n")
        elif parsed.output_file:
            sys.stdout.write(f"Report written to {parsed.output_file}\n")
        elif parsed.output_dir:
            sys.stdout.write(f"Report written to directory {parsed.output_dir}\n")

        if parsed.with_review and report.review_findings:
            return 2
        return 0
    except PermissionError as pe:
        sys.stderr.write(f"Security error: {pe}\n")
        return 2
    except Exception as e:
        sys.stderr.write(f"Reverse engineering error: {e}\n")
        return 1


def run_impact(args: list[str]) -> int:
    """CLI handler for change impact intelligence and predictive test selection."""
    import argparse
    from pathlib import Path

    from packages.review.impact.engine import ChangeImpactEngine
    from packages.review.impact.report_generator import ChangeImpactReportGenerator

    parser = argparse.ArgumentParser(
        prog="logicfalcon impact",
        description="Predictive change impact intelligence, blast-radius analysis, and test selection.",
    )
    parser.add_argument("--repo", type=str, default=".", help="Path to repository root (default: current directory).")
    parser.add_argument("--base", type=str, default=None, help="Base Git commit or branch to compare against.")
    parser.add_argument("--target", type=str, default="HEAD", help="Target Git revision (default: HEAD).")
    parser.add_argument("--staged", action="store_true", help="Analyze staged Git changes.")
    parser.add_argument("--unstaged", action="store_true", help="Analyze unstaged working tree changes.")
    parser.add_argument("--files", type=str, default=None, help="Comma-separated list of changed file paths.")
    parser.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Report format (default: markdown).")
    parser.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")
    parser.add_argument("--max-depth", type=int, default=5, help="Maximum propagation depth (default: 5).")
    parser.add_argument("--max-entities", type=int, default=500, help="Maximum entity limit (default: 500).")
    parser.add_argument("--conservative-tests", action="store_true", help="Include all repository tests in fallback mode.")
    parser.add_argument("--with-review", action="store_true", help="Execute integrated code review alongside change impact.")
    parser.add_argument("--fail-on-risk", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=None, help="Exit with code 1 if risk meets or exceeds threshold.")

    try:
        parsed = parser.parse_args(args)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    repo_path = Path(parsed.repo).resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        sys.stderr.write(f"Error: Repository path '{parsed.repo}' does not exist or is not a directory.\n")
        return 2

    explicit_files = [f.strip() for f in parsed.files.split(",") if f.strip()] if parsed.files else None

    engine = ChangeImpactEngine(
        repo_root=repo_path,
        max_depth=parsed.max_depth,
        max_entities=parsed.max_entities,
        conservative_tests=parsed.conservative_tests,
    )

    try:
        if parsed.with_review:
            report, _review_rep = engine.analyze_with_review(
                base_rev=parsed.base,
                target_rev=parsed.target,
                staged=parsed.staged,
                unstaged=parsed.unstaged,
                explicit_files=explicit_files,
            )
        else:
            report = engine.analyze(
                base_rev=parsed.base,
                target_rev=parsed.target,
                staged=parsed.staged,
                unstaged=parsed.unstaged,
                explicit_files=explicit_files,
            )

        generator = ChangeImpactReportGenerator(report)
        if parsed.output_file:
            generator.write_to_file(parsed.output_file, repo_root=repo_path)
            sys.stdout.write(f"Change impact report written to {parsed.output_file}\n")
        else:
            if parsed.format == "json":
                rendered = generator.to_json()
            elif parsed.format == "text":
                rendered = generator.to_text()
            else:
                rendered = generator.to_markdown()
            sys.stdout.write(rendered)
            if not rendered.endswith("\n"):
                sys.stdout.write("\n")

        # Risk threshold exit code handling
        if parsed.fail_on_risk:
            risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
            current_risk_val = risk_order.get(report.risk_level.value, 0)
            threshold_val = risk_order.get(parsed.fail_on_risk, 0)
            if current_risk_val >= threshold_val:
                return 1

        return 0
    except PermissionError as pe:
        sys.stderr.write(f"Security error: {pe}\n")
        return 2
    except Exception as e:
        sys.stderr.write(f"Change impact error: {e}\n")
        return 1


def run_history(args: list[str]) -> int:
    """CLI handler for historical repository intelligence and regression analytics."""
    import argparse
    import json
    from pathlib import Path

    from packages.review.history.engine import HistoricalIntelligenceEngine
    from packages.review.history.report_generator import HistoryReportGenerator

    parser = argparse.ArgumentParser(
        prog="logicfalcon history",
        description="Continuous engineering intelligence, longitudinal health trends, and regression analytics.",
    )
    subparsers = parser.add_subparsers(dest="action", help="Historical intelligence actions")

    # snapshot
    p_snap = subparsers.add_parser("snapshot", help="Capture and persist a repository health snapshot.")
    p_snap.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    p_snap.add_argument("--revision", type=str, default=None, help="Git revision or branch identifier.")
    p_snap.add_argument("--state", choices=["clean", "staged", "working_tree", "unknown"], default="unknown", help="Git working state.")
    p_snap.add_argument("--no-save", action="store_true", help="Do not persist to database.")
    p_snap.add_argument("--db", type=str, default=None, help="Custom SQLite history database path.")
    p_snap.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Report format.")
    p_snap.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")

    # list
    p_list = subparsers.add_parser("list", help="List stored repository health snapshots.")
    p_list.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    p_list.add_argument("--db", type=str, default=None, help="Custom SQLite history database path.")
    p_list.add_argument("--limit", type=int, default=50, help="Maximum number of snapshots to list.")
    p_list.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    # compare
    p_comp = subparsers.add_parser("compare", help="Compare two historical snapshots and detect regressions.")
    p_comp.add_argument("--from", dest="from_rev", required=True, type=str, help="Base snapshot ID or Git revision.")
    p_comp.add_argument("--to", dest="to_rev", required=True, type=str, help="Target snapshot ID or Git revision.")
    p_comp.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    p_comp.add_argument("--db", type=str, default=None, help="Custom SQLite history database path.")
    p_comp.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Report format.")
    p_comp.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")

    # trends
    p_trends = subparsers.add_parser("trends", help="Analyze longitudinal repository health and defect recurrence trends.")
    p_trends.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    p_trends.add_argument("--db", type=str, default=None, help="Custom SQLite history database path.")
    p_trends.add_argument("--last", type=int, default=20, help="Number of recent snapshots to analyze.")
    p_trends.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Report format.")
    p_trends.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")

    # debt
    p_debt = subparsers.add_parser("debt", help="Assess technical debt points and breakdown.")
    p_debt.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    p_debt.add_argument("--db", type=str, default=None, help="Custom SQLite history database path.")
    p_debt.add_argument("--snapshot", type=str, default=None, help="Snapshot ID or revision (default: latest).")
    p_debt.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Report format.")
    p_debt.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")

    # policy
    p_pol = subparsers.add_parser("policy", help="Evaluate engineering policy gates against snapshots or comparisons.")
    p_pol.add_argument("--config", type=str, default=None, help="Path to policy JSON configuration.")
    p_pol.add_argument("--from", dest="from_rev", type=str, default=None, help="Base snapshot ID or Git revision.")
    p_pol.add_argument("--to", dest="to_rev", type=str, default=None, help="Target snapshot ID or Git revision.")
    p_pol.add_argument("--snapshot", type=str, default=None, help="Snapshot ID or Git revision.")
    p_pol.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    p_pol.add_argument("--db", type=str, default=None, help="Custom SQLite history database path.")
    p_pol.add_argument("--format", choices=["markdown", "json", "text"], default="markdown", help="Report format.")
    p_pol.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")

    # prune
    p_prune = subparsers.add_parser("prune", help="Safely prune older snapshots beyond retention limits.")
    p_prune.add_argument("--keep", type=int, default=50, help="Number of latest snapshots to preserve.")
    p_prune.add_argument("--older-than-days", type=int, default=None, help="Delete snapshots older than N days.")
    p_prune.add_argument("--db", type=str, default=None, help="Custom SQLite history database path.")
    p_prune.add_argument("--repo", type=str, default=".", help="Path to repository root.")

    if not args:
        parser.print_help()
        return 0

    try:
        parsed = parser.parse_args(args)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    repo_path = Path(getattr(parsed, "repo", ".")).resolve()
    db_path = getattr(parsed, "db", None)
    engine = HistoricalIntelligenceEngine(repo_root=repo_path, db_path=db_path)

    try:
        if parsed.action == "snapshot":
            snapshot = engine.capture_snapshot(
                revision=parsed.revision,
                git_state=parsed.state,
                save=not parsed.no_save,
            )
            if parsed.format == "json":
                rendered = snapshot.model_dump_json(indent=2)
            else:
                rendered = HistoryReportGenerator.snapshot_to_markdown(snapshot)

            if parsed.output_file:
                HistoryReportGenerator.write_to_file(rendered, parsed.output_file, repo_root=repo_path)
                sys.stdout.write(f"Snapshot report written to {parsed.output_file}\n")
            else:
                sys.stdout.write(rendered + ("\n" if not rendered.endswith("\n") else ""))
            return 0

        elif parsed.action == "list":
            summaries = engine.storage.list_snapshots(limit=parsed.limit)
            if parsed.format == "json":
                out = [s.model_dump(mode="json") for s in summaries]
                sys.stdout.write(json.dumps(out, indent=2) + "\n")
            else:
                if not summaries:
                    sys.stdout.write("No historical snapshots found.\n")
                else:
                    sys.stdout.write(f"Historical Snapshots ({len(summaries)}):\n")
                    sys.stdout.write("-" * 80 + "\n")
                    sys.stdout.write(f"{'Snapshot ID':<38} {'Date (UTC)':<20} {'Rev':<9} {'Health':<8} {'Debt':<8} {'Findings':<8}\n")
                    sys.stdout.write("-" * 80 + "\n")
                    for s in summaries:
                        dt = s.created_at.strftime("%Y-%m-%d %H:%M")
                        rev = s.revision[:7] if s.revision else "N/A"
                        sys.stdout.write(f"{s.id!s:<38} {dt:<20} {rev:<9} {s.health_score:<8.1f} {s.tech_debt_points:<8.1f} {s.total_findings:<8}\n")
            return 0

        elif parsed.action == "compare":
            comparison = engine.compare_snapshots(from_id_or_rev=parsed.from_rev, to_id_or_rev=parsed.to_rev)
            if parsed.format == "json":
                rendered = comparison.model_dump_json(indent=2)
            else:
                rendered = HistoryReportGenerator.comparison_to_markdown(comparison)

            if parsed.output_file:
                HistoryReportGenerator.write_to_file(rendered, parsed.output_file, repo_root=repo_path)
                sys.stdout.write(f"Comparison report written to {parsed.output_file}\n")
            else:
                sys.stdout.write(rendered + ("\n" if not rendered.endswith("\n") else ""))
            return 0

        elif parsed.action == "trends":
            report = engine.analyze_trends(limit=parsed.last)
            if parsed.format == "json":
                rendered = report.model_dump_json(indent=2)
            else:
                rendered = HistoryReportGenerator.trends_to_markdown(report)

            if parsed.output_file:
                HistoryReportGenerator.write_to_file(rendered, parsed.output_file, repo_root=repo_path)
                sys.stdout.write(f"Trend report written to {parsed.output_file}\n")
            else:
                sys.stdout.write(rendered + ("\n" if not rendered.endswith("\n") else ""))
            return 0

        elif parsed.action == "debt":
            debt = engine.estimate_debt(snapshot_id=parsed.snapshot)
            if parsed.format == "json":
                rendered = debt.model_dump_json(indent=2)
            else:
                rendered = HistoryReportGenerator.debt_to_markdown(debt)

            if parsed.output_file:
                HistoryReportGenerator.write_to_file(rendered, parsed.output_file, repo_root=repo_path)
                sys.stdout.write(f"Technical debt report written to {parsed.output_file}\n")
            else:
                sys.stdout.write(rendered + ("\n" if not rendered.endswith("\n") else ""))
            return 0

        elif parsed.action == "policy":
            comp = None
            snap = None
            if parsed.from_rev and parsed.to_rev:
                comp = engine.compare_snapshots(from_id_or_rev=parsed.from_rev, to_id_or_rev=parsed.to_rev)
            elif parsed.snapshot:
                snap = engine.storage.get_snapshot(parsed.snapshot) or engine.storage.get_snapshot_by_revision(parsed.snapshot)

            res = engine.evaluate_policy(config_path=parsed.config, comparison=comp, snapshot=snap)
            if parsed.format == "json":
                rendered = res.model_dump_json(indent=2)
            else:
                rendered = HistoryReportGenerator.policy_to_markdown(res)

            if parsed.output_file:
                HistoryReportGenerator.write_to_file(rendered, parsed.output_file, repo_root=repo_path)
                sys.stdout.write(f"Policy evaluation report written to {parsed.output_file}\n")
            else:
                sys.stdout.write(rendered + ("\n" if not rendered.endswith("\n") else ""))

            return res.suggested_exit_code

        elif parsed.action == "prune":
            pruned = engine.storage.prune_snapshots(keep_last_n=parsed.keep, older_than_days=parsed.older_than_days)
            sys.stdout.write(f"Successfully pruned {pruned} historical snapshot(s).\n")
            return 0

        parser.print_help()
        return 0

    except PermissionError as pe:
        sys.stderr.write(f"Security error: {pe}\n")
        return 2
    except ValueError as ve:
        sys.stderr.write(f"Validation error: {ve}\n")
        return 2
    except Exception as e:
        sys.stderr.write(f"Historical intelligence error: {e}\n")
        return 1


def run_unified(args: list[str]) -> int:
    """CLI handler for Unified Engineering Intelligence."""
    from packages.review.unified.engine import UnifiedIntelligenceEngine
    from packages.review.unified.report_generator import UnifiedReportGenerator

    uni_parser = argparse.ArgumentParser(
        prog="logicfalcon unified",
        description="Unified Engineering Intelligence: synthesizes code review, architecture, reverse engineering, change impact, predictive tests, and historical trends into evidence-based recommendations.",
    )
    uni_parser.add_argument("--repo", type=str, default=".", help="Path to repository root.")
    uni_parser.add_argument("--staged", action="store_true", help="Analyze staged Git changes.")
    uni_parser.add_argument("--unstaged", action="store_true", help="Analyze unstaged working tree changes.")
    uni_parser.add_argument("--base", type=str, default=None, help="Base Git commit or branch to compare against.")
    uni_parser.add_argument("--target", type=str, default=None, help="Target Git revision.")
    uni_parser.add_argument("--files", type=str, default=None, help="Comma-separated list of target files.")
    uni_parser.add_argument("--save-history", action="store_true", help="Persist snapshot to historical database.")
    uni_parser.add_argument("--db", type=str, default=None, help="Path to SQLite history database.")
    uni_parser.add_argument("--policy-config", type=str, default=None, help="Path to engineering policy gate config JSON.")
    uni_parser.add_argument("--format", choices=["markdown", "json", "text"], default="text", help="Output format (default: text).")
    uni_parser.add_argument("--output-file", type=str, default=None, help="Write output report directly to file.")
    uni_parser.add_argument("--fail-on-policy", action="store_true", help="Exit code 1 if engineering policy gate fails.")

    parsed = uni_parser.parse_args(args)
    explicit_files = [f.strip() for f in parsed.files.split(",") if f.strip()] if parsed.files else None

    engine = UnifiedIntelligenceEngine(
        repo_root=parsed.repo,
        history_db_path=parsed.db,
    )

    report = engine.analyze(
        staged=parsed.staged,
        unstaged=parsed.unstaged,
        base_revision=parsed.base,
        target_revision=parsed.target,
        explicit_files=explicit_files,
        save_history=parsed.save_history,
        policy_config_path=parsed.policy_config,
    )

    gen = UnifiedReportGenerator(report)
    if parsed.format == "json":
        rendered = gen.to_json()
    elif parsed.format == "markdown":
        rendered = gen.to_markdown()
    else:
        rendered = gen.to_text()

    if parsed.output_file:
        gen.write_report(parsed.output_file, rendered)
        sys.stdout.write(f"Unified intelligence report written to {parsed.output_file}\n")
    else:
        sys.stdout.write(rendered + ("\n" if not rendered.endswith("\n") else ""))

    if parsed.fail_on_policy and not report.policy_passed:
        return 1

    return 0


def run_main(args: list[str] | None = None) -> int:
    argv = sys.argv[1:] if args is None else args

    # Handle direct review fallback when arguments start with review flags
    if argv and argv[0].startswith("-") and argv[0] not in ("-v", "--version", "-h", "--help"):
        return run_review_cli(argv)

    if not argv:
        parser = build_root_parser()
        parser.print_help()
        return 0

    if argv[0] in ("-v", "--version"):
        sys.stdout.write(f"{__product__} {__version__} (powered by {__platform__})\n")
        return 0

    if argv[0] in ("-h", "--help"):
        parser = build_root_parser()
        parser.print_help()
        return 0

    if argv[0] == "doctor":
        format_json = "--format" in argv and "json" in argv
        return run_doctor(format_json=format_json)

    if argv[0] == "capabilities":
        return run_doctor(format_json=True)

    if argv[0] == "architecture":
        return run_architecture(argv[1:])

    if argv[0] in ("reverse-engineer", "reverse_engineer"):
        return run_reverse_engineer(argv[1:])

    if argv[0] == "impact":
        return run_impact(argv[1:])

    if argv[0] == "history":
        return run_history(argv[1:])

    if argv[0] == "unified":
        return run_unified(argv[1:])

    if argv[0] == "apply-fix":
        return run_apply_fix(argv[1:])

    if argv[0] == "mcp":
        from logicfalcon.mcp.server import main as run_mcp_server
        run_mcp_server()
        return 0

    if argv[0] == "review":
        return run_review_cli(argv[1:])

    if argv[0] == "fde":
        from packages.review.fde.cli import run_fde_cli

        return run_fde_cli(argv[1:])

    if argv[0] in ("extension", "extensions"):
        from packages.review.extensions.cli import run_extension_cli

        return run_extension_cli(argv[1:])

    # Fallback to standard argparsing
    parser = build_root_parser()
    parsed = parser.parse_args(argv)
    if parsed.subcommand == "doctor":
        return run_doctor(format_json=getattr(parsed, "format", "text") == "json")
    elif parsed.subcommand == "capabilities":
        return run_doctor(format_json=True)
    elif parsed.subcommand == "architecture":
        return run_architecture(argv[1:])
    elif parsed.subcommand in ("reverse-engineer", "reverse_engineer"):
        return run_reverse_engineer(argv[1:])
    elif parsed.subcommand == "impact":
        return run_impact(argv[1:])
    elif parsed.subcommand == "history":
        return run_history(argv[1:])
    elif parsed.subcommand == "unified":
        return run_unified(argv[1:])
    elif parsed.subcommand == "apply-fix":
        return run_apply_fix(argv[1:])
    elif parsed.subcommand == "mcp":
        from logicfalcon.mcp.server import main as run_mcp_server
        run_mcp_server()
        return 0
    elif parsed.subcommand == "review":
        return run_review_cli(argv[1:])
    elif parsed.subcommand == "fde":
        from packages.review.fde.cli import run_fde_cli

        return run_fde_cli(argv[1:])
    elif parsed.subcommand in ("extension", "extensions"):
        from packages.review.extensions.cli import run_extension_cli

        return run_extension_cli(argv[1:])

    parser.print_help()
    return 0



def main() -> NoReturn:
    sys.exit(run_main())


if __name__ == "__main__":
    main()
