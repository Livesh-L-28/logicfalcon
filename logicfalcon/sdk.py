"""Programmatic Python SDK for LogicFalcon (Powered by AEGIS AI).

Provides high-level programmatic access for automated code reviews, diff inspections,
remediation verification, and safe patch applications.
"""

from pathlib import Path
from typing import Any

from packages.review.adapters.base import (
    AnalyzerRegistry,
    StaticAnalysisAdapter,
    global_analyzer_registry,
)
from packages.review.domain.models import (
    ArchitecturePolicy,
    ArchitectureReport,
    BoundaryRule,
    BoundaryViolation,
    CycleGroup,
    DependencyCycle,
    FindingSeverity,
    LayerDefinition,
    ModuleMetric,
    ProposedFix,
    ReviewFinding,
    ReviewReport,
    RuleException,
)
from packages.review.engine import LocalReviewEngine, ReviewConfig
from packages.review.extensions import (
    BaseExtension as BaseExtension,
)
from packages.review.extensions import (
    ExtensionExecutionContext as ExtensionExecutionContext,
)
from packages.review.extensions import (
    ExtensionExecutionResult as ExtensionExecutionResult,
)
from packages.review.extensions import (
    ExtensionFinding as ExtensionFinding,
)
from packages.review.extensions import (
    ExtensionHealthReport,
    ExtensionManager,
    ExtensionManifest,
    ExtensionStateRecord,
    ExtensionStorageScope,
    InstallationPlan,
)
from packages.review.extensions import (
    ExtensionRegistry as ExtensionRegistry,
)
from packages.review.extensions import (
    StaticAnalysisExtension as StaticAnalysisExtension,
)
from packages.review.extensions import (
    global_extension_registry as global_extension_registry,
)
from packages.review.fde import (
    AdapterCapability,
    AdapterExecutionResult,
    AdapterHealth,
    AdapterHealthStatus,
    AdapterRegistry,
    AwsAdapter,
    BaseAdapter,
    DeploymentDiscoveryEngine,
    DeploymentInventory,
    DeploymentRequirement,
    DiagnosticHypothesis,
    DockerAdapter,
    FailureDiagnoser,
    FdeCheckpointStore,
    FdeEvidence,
    FdeMission,
    FdeStep,
    HttpAdapter,
    InvalidStateTransitionError,
    McpAdapter,
    MissionExecutionReport,
    MissionOrchestrator,
    MissionStatus,
    OperationCategory,
    PolicyAuditRecord,
    PolicyGateway,
    PolicyViolationError,
    PostconditionResult,
    PostconditionVerifier,
    PostgresAdapter,
    PreflightFinding,
    PreflightReport,
    PreflightRunner,
    PreflightSeverity,
    PreflightStatus,
    Runbook,
    RunbookGenerator,
    RunbookInstruction,
    StepDependency,
    StepExecutionSummary,
    StepRiskLevel,
    StepStateMachine,
    StepStatus,
    VerificationOutcome,
)
from packages.review.fix_engine import (
    FixApplicationResult,
    RemediationVerificationResult,
    ReviewFixEngine,
)
from packages.review.history.engine import HistoricalIntelligenceEngine
from packages.review.history.models import (
    EngineeringTrendReport,
    FindingLifecycleState,
    PolicyEvaluationResult,
    PolicyMode,
    PolicyRule,
    RepositoryMetrics,
    RepositorySnapshot,
    SnapshotComparison,
    SnapshotFinding,
    SnapshotMetadata,
    SnapshotSummary,
    TechnicalDebtEstimate,
    TrendDirection,
)
from packages.review.history.policy import EngineeringPolicyEvaluator
from packages.review.history.report_generator import HistoryReportGenerator
from packages.review.history.storage import HistoryStorage
from packages.review.impact.engine import ChangeImpactEngine
from packages.review.impact.models import (
    ChangeImpactReport,
    ChangeSet,
    ImpactedEntity,
    ImpactRiskLevel,
    ImpactType,
    TestImpactCandidate,
)
from packages.review.reverse_engineering.engine import ReverseEngineeringEngine
from packages.review.reverse_engineering.models import ReverseEngineeringReport
from packages.review.unified.engine import UnifiedIntelligenceEngine
from packages.review.unified.models import (
    RecommendationCategory,
    RecommendationPriority,
    UnifiedIntelligenceReport,
    UnifiedRecommendation,
)
from packages.review.unified.recommendations import RecommendationSynthesizer
from packages.review.unified.report_generator import UnifiedReportGenerator
from packages.review.validator import FindingValidator

__all__ = [
    "AdapterCapability",
    "AdapterExecutionResult",
    "AdapterHealth",
    "AdapterHealthStatus",
    "AdapterRegistry",
    "AnalyzerRegistry",
    "ArchitecturePolicy",
    "ArchitectureReport",
    "AwsAdapter",
    "BaseAdapter",
    "BoundaryRule",
    "BoundaryViolation",
    "ChangeImpactEngine",
    "ChangeImpactReport",
    "ChangeSet",
    "CycleGroup",
    "DependencyCycle",
    "DeploymentDiscoveryEngine",
    "DeploymentInventory",
    "DeploymentRequirement",
    "DiagnosticHypothesis",
    "DockerAdapter",
    "EngineeringPolicyEvaluator",
    "EngineeringTrendReport",
    "FailureDiagnoser",
    "FdeCheckpointStore",
    "FdeEvidence",
    "FdeMission",
    "FdeStep",
    "FindingLifecycleState",
    "FindingSeverity",
    "FindingValidator",
    "FixApplicationResult",
    "HistoricalIntelligenceEngine",
    "HistoryReportGenerator",
    "HistoryStorage",
    "HttpAdapter",
    "ImpactRiskLevel",
    "ImpactType",
    "ImpactedEntity",
    "InvalidStateTransitionError",
    "LayerDefinition",
    "LocalReviewEngine",
    "McpAdapter",
    "MissionExecutionReport",
    "MissionOrchestrator",
    "MissionStatus",
    "ModuleMetric",
    "OperationCategory",
    "PolicyAuditRecord",
    "PolicyEvaluationResult",
    "PolicyGateway",
    "PolicyMode",
    "PolicyRule",
    "PolicyViolationError",
    "PostconditionResult",
    "PostconditionVerifier",
    "PostgresAdapter",
    "PreflightFinding",
    "PreflightReport",
    "PreflightRunner",
    "PreflightSeverity",
    "PreflightStatus",
    "ProposedFix",
    "RecommendationCategory",
    "RecommendationPriority",
    "RecommendationSynthesizer",
    "RemediationVerificationResult",
    "RepositoryMetrics",
    "RepositorySnapshot",
    "ReverseEngineeringEngine",
    "ReverseEngineeringReport",
    "ReviewConfig",
    "ReviewFinding",
    "ReviewFixEngine",
    "ReviewReport",
    "RuleException",
    "Runbook",
    "RunbookGenerator",
    "RunbookInstruction",
    "SnapshotComparison",
    "SnapshotFinding",
    "SnapshotMetadata",
    "SnapshotSummary",
    "StaticAnalysisAdapter",
    "StepDependency",
    "StepExecutionSummary",
    "StepRiskLevel",
    "StepStateMachine",
    "StepStatus",
    "TechnicalDebtEstimate",
    "TestImpactCandidate",
    "TrendDirection",
    "UnifiedIntelligenceEngine",
    "UnifiedIntelligenceReport",
    "UnifiedRecommendation",
    "UnifiedReportGenerator",
    "VerificationOutcome",
    "analyze_architecture",
    "analyze_impact",
    "analyze_impact_with_review",
    "analyze_trends",
    "analyze_unified",
    "apply_fix",
    "capture_snapshot",
    "compare_snapshots",
    "estimate_debt",
    "evaluate_history_policy",
    "fde_generate_runbook",
    "fde_inspect",
    "fde_plan",
    "fde_preflight",
    "fde_run_mission",
    "global_analyzer_registry",
    "list_snapshots",
    "reverse_engineer",
    "reverse_engineer_with_review",
    "review",
    "review_diff",
    "review_file",
    "review_workspace",
    "verify_fix",
]




def review_file(
    file_path: str | Path,
    repo_root: str | Path = ".",
    content: str | None = None,
    config: ReviewConfig | None = None,
) -> ReviewReport:
    """Executes a code review on a single target file on disk or an in-memory buffer.

    Args:
        file_path: Path to target file (relative to repo or absolute within repo).
        repo_root: Path to repository root.
        content: Optional buffer content (for unsaved editor documents).
        config: Custom ReviewConfig options.

    Returns:
        ReviewReport containing findings and execution metrics.
    """
    repo_path = Path(repo_root).resolve()
    engine_config = config or ReviewConfig()
    engine = LocalReviewEngine(repo_root=repo_path, config=engine_config)
    return engine.review_file(file_path=file_path, content=content)


def review_workspace(
    repo_root: str | Path = ".",
    config: ReviewConfig | None = None,
    max_files: int = 1000,
) -> ReviewReport:
    """Executes a code review across supported source files in the workspace.

    Args:
        repo_root: Path to workspace/repository root.
        config: Custom ReviewConfig options.
        max_files: Maximum number of files to inspect.

    Returns:
        ReviewReport containing aggregated findings.
    """
    repo_path = Path(repo_root).resolve()
    engine_config = config or ReviewConfig()
    engine = LocalReviewEngine(repo_root=repo_path, config=engine_config)

    discovered_files: list[str] = []
    for ext in (".py", ".ts", ".js", ".tsx", ".jsx"):
        for p in repo_path.rglob(f"*{ext}"):
            if p.is_file():
                try:
                    rel = str(p.relative_to(repo_path))
                    if not engine._is_ignored(rel):
                        discovered_files.append(rel)
                        if len(discovered_files) >= max_files:
                            break
                except ValueError:
                    continue
        if len(discovered_files) >= max_files:
            break

    return engine.review_files(discovered_files)



def review(
    repo: str | Path = ".",
    base: str | None = None,
    staged: bool = False,
    unstaged: bool = False,
    severity_threshold: str = "ERROR",
    include_re_context: bool = False,
    config: ReviewConfig | None = None,
) -> ReviewReport:
    """Executes a code review on a repository or working tree diff.

    Args:
        repo: Path to target repository root.
        base: Git commit or branch ref to compare against (e.g. 'origin/main').
        staged: If True, reviews only staged (cached) Git changes.
        unstaged: If True, reviews only unstaged working tree changes.
        severity_threshold: Minimum severity to trigger failure.
        include_re_context: If True, enriches findings with reverse engineering intelligence.
        config: Custom ReviewConfig options.

    Returns:
        ReviewReport containing findings, affected artifacts, and execution metrics.
    """
    repo_path = Path(repo).resolve()
    engine_config = config or ReviewConfig()
    if include_re_context:
        engine_config.include_re_context = True
    engine = LocalReviewEngine(repo_root=repo_path, config=engine_config)

    report = engine.review_local_git_diff(
        base_ref=base,
        staged=staged,
        unstaged=unstaged,
    )

    validator = FindingValidator(repo_root=repo_path)
    verified, _ = validator.validate(report.findings)
    report.findings = verified
    return report


def review_diff(
    diff_text: str,
    repo_root: str | Path = ".",
    config: ReviewConfig | None = None,
) -> ReviewReport:
    """Synchronously reviews a raw unified Git diff string.

    Args:
        diff_text: Unified git diff formatted text.
        repo_root: Path to repository root for context and validation.
        config: Custom ReviewConfig options.

    Returns:
        ReviewReport containing findings and analysis metadata.
    """
    repo_path = Path(repo_root).resolve()
    engine_config = config or ReviewConfig()
    engine = LocalReviewEngine(repo_root=repo_path, config=engine_config)
    report = engine.review_diff(diff_text=diff_text)

    diff_summary = engine.diff_parser.parse(diff_text)
    validator = FindingValidator(repo_root=repo_path)
    verified, _ = validator.validate(report.findings, diff_summary=diff_summary)
    report.findings = verified
    return report


def apply_fix(
    fix: ProposedFix,
    approved: bool = False,
    repo_root: str | Path = ".",
    dry_run: bool = False,
    validate_syntax: bool = True,
    create_backup: bool = True,
) -> FixApplicationResult:
    """Safely applies a proposed remediation fix to disk.

    Args:
        fix: ProposedFix object to apply.
        approved: Explicit developer confirmation (required if dry_run=False).
        repo_root: Target repository root.
        dry_run: If True, returns unified diff preview without modifying disk.
        validate_syntax: If True, checks python syntax before writing.
        create_backup: If True, creates a .bak copy before modifying.

    Returns:
        FixApplicationResult with execution status and diff.
    """
    repo_path = Path(repo_root).resolve()
    fix_engine = ReviewFixEngine(repo_root=repo_path)
    return fix_engine.apply_fix(
        fix=fix,
        approved=approved,
        dry_run=dry_run,
        validate_syntax=validate_syntax,
        create_backup=create_backup,
    )


def verify_fix(
    fixes: list[ProposedFix],
    repo_root: str | Path = ".",
    run_tests: bool = True,
    run_linters: bool = True,
    test_command: list[str] | None = None,
    lint_command: list[str] | None = None,
) -> RemediationVerificationResult:
    """Applies fixes in an isolated workspace and runs real tests and linters.

    Args:
        fixes: List of ProposedFix objects to verify.
        repo_root: Target repository root.
        run_tests: Whether to execute tests in the isolated workspace.
        run_linters: Whether to execute linters in the isolated workspace.
        test_command: Custom test command list (e.g. ['pytest', 'tests/']).
        lint_command: Custom linter command list (e.g. ['ruff', 'check', '.']).

    Returns:
        RemediationVerificationResult indicating whether the fix passed QA.
    """
    repo_path = Path(repo_root).resolve()
    fix_engine = ReviewFixEngine(repo_root=repo_path)
    return fix_engine.verify_remediation(
        fixes=fixes,
        run_tests=run_tests,
        run_linters=run_linters,
        test_command=test_command,
        lint_command=lint_command,
    )


def analyze_architecture(
    repo: str | Path = ".",
    boundary_rules: list[dict[str, str]] | None = None,
    policy: ArchitecturePolicy | None = None,
) -> ArchitectureReport:
    """Analyzes repository modularity, circular dependencies, boundary violations, and architecture health score.

    Args:
        repo: Path to target repository root.
        boundary_rules: Optional list of custom architectural boundary rules.
        policy: Optional ArchitecturePolicy with layer constraints and exceptions.

    Returns:
        ArchitectureReport with cycles, cycle groups, boundary violations, coupling metrics, and health score.
    """
    repo_path = Path(repo).resolve()
    from packages.review.analyzer.architecture import ArchitectureAnalyzer

    analyzer = ArchitectureAnalyzer(
        repo_root=repo_path,
        boundary_rules=boundary_rules,
        policy=policy,
    )
    return analyzer.analyze()


def reverse_engineer(
    repo_root: str | Path = ".",
    max_file_size_bytes: int = 1_000_000,
    max_depth: int = 15,
    timeout_seconds: float = 60.0,
    exclude_dirs: set[str] | None = None,
    run_review: bool = False,
    review_config: ReviewConfig | None = None,
    format_type: str | None = None,
) -> Any:
    """Executes safe, read-only reverse engineering reconnaissance and architecture reconstruction.

    Args:
        repo_root: Path to target repository root (default: current directory).
        max_file_size_bytes: Maximum file size to inspect (default: 1,000,000 bytes).
        max_depth: Maximum directory depth to traverse (default: 15).
        timeout_seconds: Maximum analysis timeout in seconds (default: 60.0).
        exclude_dirs: Optional set of directory names to skip during scan.
        run_review: If True, executes integrated code review across discovered files.
        review_config: Optional custom ReviewConfig for integrated review.
        format_type: Optional report format ('json', 'markdown', or 'text'). If None, returns ReverseEngineeringReport.

    Returns:
        ReverseEngineeringReport object or formatted report string (JSON, Markdown, or Plain Text).
    """
    engine = ReverseEngineeringEngine(
        repo_root=repo_root,
        max_file_size_bytes=max_file_size_bytes,
        max_depth=max_depth,
        timeout_seconds=timeout_seconds,
        exclude_dirs=exclude_dirs,
    )
    report = (
        engine.analyze_with_review(run_review=True, review_config=review_config)
        if run_review
        else engine.analyze()
    )

    if format_type == "json":
        return report.model_dump_json(indent=2)
    elif format_type in ("markdown", "md"):
        from packages.review.reverse_engineering.report_generator import ReportGenerator

        return ReportGenerator(report).to_markdown()
    elif format_type == "text":
        from packages.review.reverse_engineering.report_generator import ReportGenerator

        return ReportGenerator(report).to_text()
    return report


def reverse_engineer_with_review(
    repo_root: str | Path = ".",
    max_file_size_bytes: int = 1_000_000,
    max_depth: int = 15,
    timeout_seconds: float = 60.0,
    exclude_dirs: set[str] | None = None,
    review_config: ReviewConfig | None = None,
    format_type: str | None = None,
) -> Any:
    """Convenience helper to execute reverse engineering reconnaissance with integrated code review."""
    return reverse_engineer(
        repo_root=repo_root,
        max_file_size_bytes=max_file_size_bytes,
        max_depth=max_depth,
        timeout_seconds=timeout_seconds,
        exclude_dirs=exclude_dirs,
        run_review=True,
        review_config=review_config,
        format_type=format_type,
    )


def analyze_impact(
    repo_root: str | Path = ".",
    base_rev: str | None = None,
    target_rev: str | None = None,
    staged: bool = False,
    unstaged: bool = False,
    explicit_files: list[str] | None = None,
    max_depth: int = 5,
    max_entities: int = 500,
    conservative_tests: bool = False,
    format_type: str | None = None,
) -> Any:
    """Executes change impact analysis and predictive test selection on changes.

    Args:
        repo_root: Path to target repository root (default: current directory).
        base_rev: Optional base Git revision or branch.
        target_rev: Optional target Git revision (default: HEAD).
        staged: If True, inspects staged changes.
        unstaged: If True, inspects unstaged changes.
        explicit_files: Optional explicit list of modified file paths.
        max_depth: Maximum dependency propagation depth (default: 5).
        max_entities: Maximum impacted entity count (default: 500).
        conservative_tests: If True, recommends all discovered repository tests.
        format_type: Optional output format ('json', 'markdown', or 'text').

    Returns:
        ChangeImpactReport or serialized report string.
    """
    engine = ChangeImpactEngine(
        repo_root=repo_root,
        max_depth=max_depth,
        max_entities=max_entities,
        conservative_tests=conservative_tests,
    )
    report = engine.analyze(
        base_rev=base_rev,
        target_rev=target_rev,
        staged=staged,
        unstaged=unstaged,
        explicit_files=explicit_files,
    )

    if format_type == "json":
        return report.model_dump_json(indent=2)
    elif format_type in ("markdown", "md"):
        from packages.review.impact.report_generator import ChangeImpactReportGenerator

        return ChangeImpactReportGenerator(report).to_markdown()
    elif format_type == "text":
        from packages.review.impact.report_generator import ChangeImpactReportGenerator

        return ChangeImpactReportGenerator(report).to_text()
    return report


def analyze_impact_with_review(
    repo_root: str | Path = ".",
    base_rev: str | None = None,
    target_rev: str | None = None,
    staged: bool = False,
    unstaged: bool = False,
    explicit_files: list[str] | None = None,
    max_depth: int = 5,
    max_entities: int = 500,
    conservative_tests: bool = False,
) -> tuple[ChangeImpactReport, ReviewReport]:
    """Executes change impact analysis and automated code review together."""
    engine = ChangeImpactEngine(
        repo_root=repo_root,
        max_depth=max_depth,
        max_entities=max_entities,
        conservative_tests=conservative_tests,
    )
    return engine.analyze_with_review(
        base_rev=base_rev,
        target_rev=target_rev,
        staged=staged,
        unstaged=unstaged,
        explicit_files=explicit_files,
    )


def capture_snapshot(
    repo_root: str | Path = ".",
    revision: str | None = None,
    git_state: str = "unknown",
    save: bool = True,
    db_path: str | Path | None = None,
    max_files: int = 500,
    format_type: str | None = None,
) -> Any:
    """Captures and optionally persists a comprehensive repository engineering health snapshot.

    Args:
        repo_root: Path to workspace/repository root.
        revision: Optional Git commit or branch identifier.
        git_state: Git working state ('clean', 'staged', 'working_tree', 'unknown').
        save: If True, persists snapshot to history database.
        db_path: Optional custom path to SQLite database.
        max_files: Maximum files to scan.
        format_type: Output format ('json', 'markdown', or 'text').

    Returns:
        RepositorySnapshot object or serialized formatted string.
    """
    engine = HistoricalIntelligenceEngine(repo_root=repo_root, db_path=db_path)
    snapshot = engine.capture_snapshot(
        revision=revision,
        git_state=git_state,
        save=save,
        max_files=max_files,
    )

    if format_type == "json":
        return snapshot.model_dump_json(indent=2)
    elif format_type in ("markdown", "md"):
        return HistoryReportGenerator.snapshot_to_markdown(snapshot)
    return snapshot


def list_snapshots(
    repo_root: str | Path = ".",
    db_path: str | Path | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SnapshotSummary]:
    """Retrieves paginated historical snapshot summaries."""
    engine = HistoricalIntelligenceEngine(repo_root=repo_root, db_path=db_path)
    return engine.storage.list_snapshots(limit=limit, offset=offset)


def compare_snapshots(
    from_id_or_rev: str,
    to_id_or_rev: str,
    repo_root: str | Path = ".",
    db_path: str | Path | None = None,
    format_type: str | None = None,
) -> Any:
    """Compares two historical snapshots and detects regressions, deltas, and lifecycle changes."""
    engine = HistoricalIntelligenceEngine(repo_root=repo_root, db_path=db_path)
    comparison = engine.compare_snapshots(from_id_or_rev=from_id_or_rev, to_id_or_rev=to_id_or_rev)

    if format_type == "json":
        return comparison.model_dump_json(indent=2)
    elif format_type in ("markdown", "md"):
        return HistoryReportGenerator.comparison_to_markdown(comparison)
    return comparison


def analyze_trends(
    repo_root: str | Path = ".",
    db_path: str | Path | None = None,
    limit: int = 20,
    format_type: str | None = None,
) -> Any:
    """Computes longitudinal repository health, technical debt, and defect recurrence trends."""
    engine = HistoricalIntelligenceEngine(repo_root=repo_root, db_path=db_path)
    report = engine.analyze_trends(limit=limit)

    if format_type == "json":
        return report.model_dump_json(indent=2)
    elif format_type in ("markdown", "md"):
        return HistoryReportGenerator.trends_to_markdown(report)
    return report


def estimate_debt(
    repo_root: str | Path = ".",
    db_path: str | Path | None = None,
    snapshot_id: str | None = None,
    format_type: str | None = None,
) -> Any:
    """Computes technical debt point estimate and breakdowns."""
    engine = HistoricalIntelligenceEngine(repo_root=repo_root, db_path=db_path)
    debt = engine.estimate_debt(snapshot_id=snapshot_id)

    if format_type == "json":
        return debt.model_dump_json(indent=2)
    elif format_type in ("markdown", "md"):
        return HistoryReportGenerator.debt_to_markdown(debt)
    return debt


def evaluate_history_policy(
    repo_root: str | Path = ".",
    db_path: str | Path | None = None,
    config_path: str | Path | None = None,
    from_id_or_rev: str | None = None,
    to_id_or_rev: str | None = None,
    snapshot_id: str | None = None,
    format_type: str | None = None,
) -> Any:
    """Evaluates engineering policy gates against a revision comparison or repository snapshot."""
    engine = HistoricalIntelligenceEngine(repo_root=repo_root, db_path=db_path)

    comparison = None
    snapshot = None
    if from_id_or_rev and to_id_or_rev:
        comparison = engine.compare_snapshots(from_id_or_rev=from_id_or_rev, to_id_or_rev=to_id_or_rev)
    elif snapshot_id:
        snapshot = engine.storage.get_snapshot(snapshot_id) or engine.storage.get_snapshot_by_revision(snapshot_id)

    result = engine.evaluate_policy(
        config_path=config_path,
        comparison=comparison,
        snapshot=snapshot,
    )

    if format_type == "json":
        return result.model_dump_json(indent=2)
    elif format_type in ("markdown", "md"):
        return HistoryReportGenerator.policy_to_markdown(result)
    return result


def analyze_unified(
    repo_root: str | Path = ".",
    staged: bool = False,
    unstaged: bool = False,
    base_revision: str | None = None,
    target_revision: str | None = None,
    explicit_files: list[str] | None = None,
    save_history: bool = False,
    history_db_path: str | Path | None = None,
    revision: str | None = None,
    policy_config_path: str | Path | None = None,
    max_files: int = 500,
    format_type: str | None = None,
    output_file: str | Path | None = None,
) -> Any:
    """Executes a unified engineering intelligence pass across all LogicFalcon capabilities.

    Coordinates code review, architecture analysis, reverse engineering, change-impact
    assessment, predictive test selection, historical tracking, and evidence-grounded
    recommendations.
    """
    engine = UnifiedIntelligenceEngine(
        repo_root=repo_root,
        history_db_path=history_db_path,
        max_files=max_files,
    )
    report = engine.analyze(
        staged=staged,
        unstaged=unstaged,
        base_revision=base_revision,
        target_revision=target_revision,
        explicit_files=explicit_files,
        save_history=save_history,
        revision=revision,
        policy_config_path=policy_config_path,
    )

    generator = UnifiedReportGenerator(report)

    if output_file:
        if format_type == "json":
            out_content = generator.to_json()
        elif format_type == "text":
            out_content = generator.to_text()
        else:
            out_content = generator.to_markdown()
        generator.write_report(output_file, out_content)

    if format_type == "json":
        return generator.to_json()
    elif format_type in ("markdown", "md"):
        return generator.to_markdown()
    elif format_type == "text":
        return generator.to_text()

    return report


def fde_inspect(
    repo_root: str | Path = ".",
) -> DeploymentInventory:
    """Discover deployment requirements, frameworks, databases, and container specs statically."""
    engine = DeploymentDiscoveryEngine(repo_root=Path(repo_root))
    return engine.discover()


def fde_preflight(
    repo_root: str | Path = ".",
    check_docker: bool = False,
    check_ports: bool = True,
    check_env_vars: bool = True,
    check_dns: bool = False,
    dns_hosts: list[str] | None = None,
    http_health_url: str | None = None,
) -> PreflightReport:
    """Run non-destructive preflight validation probes for runtime, ports, DNS, and endpoints."""
    runner = PreflightRunner(
        repo_root=Path(repo_root),
        check_docker=check_docker,
        check_ports=check_ports,
        check_env_vars=check_env_vars,
        check_dns=check_dns,
        dns_hosts=dns_hosts,
        http_health_url=http_health_url,
    )
    return runner.run_preflight()


def fde_plan(
    repo_root: str | Path = ".",
) -> FdeMission:
    """Generate a deployment mission DAG based on static inspection of the repository."""
    inventory = fde_inspect(repo_root=repo_root)
    steps = [
        FdeStep(
            id="validate-runtime",
            name="Validate Runtime Environment",
            description="Verify Python runtime environment meets minimum version requirements.",
            operation_category=OperationCategory.READ_ONLY,
            risk_level=StepRiskLevel.LOW,
            operation="probe_runtime",
            target="python",
        ),
    ]

    if inventory.database_types:
        for db in inventory.database_types:
            steps.append(
                FdeStep(
                    id=f"verify-db-{db.lower()}",
                    name=f"Verify {db} Database Reachability",
                    description=f"Perform read-only validation check on configured {db} instance.",
                    operation_category=OperationCategory.READ_ONLY,
                    risk_level=StepRiskLevel.LOW,
                    operation="postgres_ping" if db.lower() == "postgresql" else "db_ping",
                    target=db.lower(),
                    dependencies=[StepDependency(step_id="validate-runtime")],
                )
            )

    if inventory.declared_ports:
        for port in inventory.declared_ports:
            steps.append(
                FdeStep(
                    id=f"check-port-{port}",
                    name=f"Check Port {port} Availability",
                    description=f"Ensure application port {port} is not already bound by another process.",
                    operation_category=OperationCategory.READ_ONLY,
                    risk_level=StepRiskLevel.LOW,
                    operation="probe_port",
                    target=str(port),
                    dependencies=[StepDependency(step_id="validate-runtime")],
                )
            )

    return FdeMission(
        name="Automated FDE Deployment Plan",
        objective="Validate repository deployment readiness and verify runtime prerequisites.",
        steps=steps,
    )


def fde_generate_runbook(
    mission: FdeMission,
    inventory: DeploymentInventory | None = None,
    execution_report: MissionExecutionReport | None = None,
) -> Runbook:
    """Generate an operator deployment and verification runbook from an FDE mission."""
    generator = RunbookGenerator()
    return generator.generate_runbook(
        mission=mission,
        inventory=inventory,
        execution_report=execution_report,
    )


def fde_run_mission(
    mission: FdeMission,
    registry: AdapterRegistry | None = None,
    approval_tokens: dict[str, str] | None = None,
) -> MissionExecutionReport:
    """Execute an authorized FDE mission DAG through the policy gateway with postcondition verification."""
    from packages.review.fde.cli import _build_default_registry

    reg = registry or _build_default_registry()
    gateway = PolicyGateway(reg)
    orchestrator = MissionOrchestrator(
        registry=reg,
        policy_gateway=gateway,
    )
    return orchestrator.run_mission(mission, approval_tokens=approval_tokens or {})


def list_extensions(
    workspace_dir: Path | None = None,
    user_dir: Path | None = None,
) -> list[tuple[ExtensionManifest, ExtensionStateRecord]]:
    """Discover and return all installed LogicFalcon extensions across scopes."""
    manager = ExtensionManager(workspace_dir=workspace_dir, user_dir=user_dir)
    return manager.discover()


def get_extension(
    extension_id: str,
    workspace_dir: Path | None = None,
    user_dir: Path | None = None,
) -> ExtensionManifest | None:
    """Retrieve metadata for an installed extension by ID."""
    manager = ExtensionManager(workspace_dir=workspace_dir, user_dir=user_dir)
    manager.discover()
    entry = manager.registry.get(extension_id)
    return entry.manifest if entry else None


def install_extension(
    source: str | Path,
    workspace: bool = False,
    dry_run: bool = False,
    workspace_dir: Path | None = None,
    user_dir: Path | None = None,
) -> InstallationPlan:
    """Install or preview installation of a LogicFalcon extension."""
    manager = ExtensionManager(workspace_dir=workspace_dir, user_dir=user_dir)
    scope = ExtensionStorageScope.WORKSPACE if workspace else ExtensionStorageScope.USER
    return manager.install(source, scope=scope, dry_run=dry_run)


def enable_extension(
    extension_id: str,
    workspace_dir: Path | None = None,
    user_dir: Path | None = None,
) -> ExtensionStateRecord:
    """Enable an installed extension."""
    manager = ExtensionManager(workspace_dir=workspace_dir, user_dir=user_dir)
    return manager.enable(extension_id)


def disable_extension(
    extension_id: str,
    workspace_dir: Path | None = None,
    user_dir: Path | None = None,
) -> ExtensionStateRecord:
    """Disable an active extension."""
    manager = ExtensionManager(workspace_dir=workspace_dir, user_dir=user_dir)
    return manager.disable(extension_id)


def uninstall_extension(
    extension_id: str,
    purge_config: bool = False,
    workspace_dir: Path | None = None,
    user_dir: Path | None = None,
) -> None:
    """Uninstall an extension, optionally purging saved configuration."""
    manager = ExtensionManager(workspace_dir=workspace_dir, user_dir=user_dir)
    manager.uninstall(extension_id, purge_config=purge_config)


def diagnose_extensions(
    workspace_dir: Path | None = None,
    user_dir: Path | None = None,
) -> list[ExtensionHealthReport]:
    """Run non-destructive diagnostic health checks on all installed extensions."""
    manager = ExtensionManager(workspace_dir=workspace_dir, user_dir=user_dir)
    return manager.diagnose()

