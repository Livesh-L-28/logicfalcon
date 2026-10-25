"""LogicFalcon — Fast, precise engineering intelligence. Powered by AEGIS AI.

LogicFalcon is an AI-powered software engineering intelligence platform for
evidence-grounded code review, repository analysis, change-impact assessment,
root-cause analysis, and safe fix proposals. Powered by AEGIS AI.
"""

__version__ = "0.1.5"
__product__ = "LogicFalcon"
__tagline__ = "Fast, precise engineering intelligence."
__platform__ = "AEGIS AI"

try:
    from packages.intelligence.debugging.service import AutonomousDebuggingService
except (ImportError, ModuleNotFoundError):
    class AutonomousDebuggingService:  # type: ignore[no-redef]
        """Autonomous debugging service requires the full AEGIS AI platform backend.

        This feature is unavailable in the standalone LogicFalcon CLI/SDK distribution.
        """

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError(
                "AutonomousDebuggingService requires the optional AEGIS AI platform backend (apps.api). "
                "It is not available in the standalone LogicFalcon CLI/SDK distribution."
            )

from logicfalcon.sdk import (
    BaseExtension,
    DeploymentInventory,
    ExtensionExecutionContext,
    ExtensionExecutionResult,
    ExtensionFinding,
    ExtensionHealthReport,
    ExtensionManager,
    ExtensionManifest,
    ExtensionRegistry,
    ExtensionStateRecord,
    ExtensionStorageScope,
    FdeMission,
    FdeStep,
    InstallationPlan,
    MissionOrchestrator,
    MissionStatus,
    OperationCategory,
    PolicyGateway,
    PreflightReport,
    Runbook,
    StaticAnalysisExtension,
    analyze_architecture,
    analyze_impact,
    analyze_impact_with_review,
    analyze_trends,
    analyze_unified,
    apply_fix,
    capture_snapshot,
    compare_snapshots,
    diagnose_extensions,
    disable_extension,
    enable_extension,
    estimate_debt,
    evaluate_history_policy,
    fde_generate_runbook,
    fde_inspect,
    fde_plan,
    fde_preflight,
    fde_run_mission,
    get_extension,
    install_extension,
    list_extensions,
    list_snapshots,
    reverse_engineer,
    reverse_engineer_with_review,
    review,
    review_diff,
    review_file,
    review_workspace,
    uninstall_extension,
    verify_fix,
)
from packages.review.adapters.base import (
    AnalyzerRegistry,
    StaticAnalysisAdapter,
    global_analyzer_registry,
)
from packages.review.analyzer.architecture import ArchitectureAnalyzer
from packages.review.cli import build_parser, run_cli
from packages.review.domain.models import (
    ArchitecturePolicy,
    ArchitectureReport,
    BoundaryRule,
    BoundaryViolation,
    CycleGroup,
    DependencyCycle,
    FindingCategory,
    FindingSeverity,
    LayerDefinition,
    ModuleMetric,
    ProposedFix,
    ReviewFinding,
    ReviewReport,
    RuleException,
    ValidationStatus,
)
from packages.review.engine import LocalReviewEngine, ReviewConfig
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
    "AnalyzerRegistry",
    "ArchitectureAnalyzer",
    "ArchitecturePolicy",
    "ArchitectureReport",
    "AutonomousDebuggingService",
    "BaseExtension",
    "BoundaryRule",
    "BoundaryViolation",
    "ChangeImpactEngine",
    "ChangeImpactReport",
    "ChangeSet",
    "CycleGroup",
    "DependencyCycle",
    "DeploymentInventory",
    "EngineeringPolicyEvaluator",
    "EngineeringTrendReport",
    "ExtensionExecutionContext",
    "ExtensionExecutionResult",
    "ExtensionFinding",
    "ExtensionHealthReport",
    "ExtensionManager",
    "ExtensionManifest",
    "ExtensionRegistry",
    "ExtensionStateRecord",
    "ExtensionStorageScope",
    "FdeMission",
    "FdeStep",
    "FindingCategory",
    "FindingLifecycleState",
    "FindingSeverity",
    "FindingValidator",
    "FixApplicationResult",
    "HistoricalIntelligenceEngine",
    "HistoryReportGenerator",
    "HistoryStorage",
    "ImpactRiskLevel",
    "ImpactType",
    "ImpactedEntity",
    "InstallationPlan",
    "LayerDefinition",
    "LocalReviewEngine",
    "MissionOrchestrator",
    "MissionStatus",
    "ModuleMetric",
    "OperationCategory",
    "PolicyAuditRecord",
    "PolicyEvaluationResult",
    "PolicyGateway",
    "PolicyMode",
    "PolicyRule",
    "PreflightReport",
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
    "SnapshotComparison",
    "SnapshotFinding",
    "SnapshotMetadata",
    "SnapshotSummary",
    "StaticAnalysisAdapter",
    "StaticAnalysisExtension",
    "TechnicalDebtEstimate",
    "TestImpactCandidate",
    "TrendDirection",
    "UnifiedIntelligenceEngine",
    "UnifiedIntelligenceReport",
    "UnifiedRecommendation",
    "UnifiedReportGenerator",
    "ValidationStatus",
    "__platform__",
    "__product__",
    "__tagline__",
    "__version__",
    "analyze_architecture",
    "analyze_impact",
    "analyze_impact_with_review",
    "analyze_trends",
    "analyze_unified",
    "apply_fix",
    "build_parser",
    "capture_snapshot",
    "compare_snapshots",
    "diagnose_extensions",
    "disable_extension",
    "enable_extension",
    "estimate_debt",
    "evaluate_history_policy",
    "fde_generate_runbook",
    "fde_inspect",
    "fde_plan",
    "fde_preflight",
    "fde_run_mission",
    "get_extension",
    "global_analyzer_registry",
    "install_extension",
    "list_extensions",
    "list_snapshots",
    "reverse_engineer",
    "reverse_engineer_with_review",
    "review",
    "review_diff",
    "review_file",
    "review_workspace",
    "run_cli",
    "uninstall_extension",
    "verify_fix",
]



