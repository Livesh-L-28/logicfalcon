"""Developer SDK contracts, base classes, and execution context for LogicFalcon extensions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packages.review.extensions.models import ExtensionManifest


@dataclass
class ExtensionExecutionContext:
    """Runtime execution context provided to extensions during invocation."""

    extension_id: str
    workspace_root: Path
    config: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtensionFinding:
    """Standardized finding produced by an extension."""

    rule_id: str
    title: str
    message: str
    file_path: str
    start_line: int
    end_line: int | None = None
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL
    suggestion: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtensionExecutionResult:
    """Structured response returned by an extension execution."""

    success: bool
    findings: list[ExtensionFinding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    output: str | None = None


class BaseExtension(ABC):
    """Abstract base class that all in-process LogicFalcon extensions inherit from."""

    def __init__(self, manifest: ExtensionManifest | None = None) -> None:
        self.manifest = manifest

    def initialize(self, context: ExtensionExecutionContext) -> None:  # noqa: B027
        """Invoked once when the extension is loaded and initialized."""
        pass

    @abstractmethod
    def execute(
        self,
        target_files: list[Path],
        context: ExtensionExecutionContext,
    ) -> ExtensionExecutionResult:
        """Core execution logic performed by the extension on the provided target files."""
        raise NotImplementedError

    def teardown(self) -> None:  # noqa: B027
        """Invoked when the extension is disabled or unloaded."""
        pass


class StaticAnalysisExtension(BaseExtension):
    """Specialized base class for deterministic static analysis and AST rule extensions."""

    @abstractmethod
    def analyze_file(self, file_path: Path, context: ExtensionExecutionContext) -> list[ExtensionFinding]:
        """Analyzes a single source file and returns any identified findings."""
        raise NotImplementedError

    def execute(
        self,
        target_files: list[Path],
        context: ExtensionExecutionContext,
    ) -> ExtensionExecutionResult:
        all_findings: list[ExtensionFinding] = []
        files_analyzed = 0

        for path in target_files:
            if not path.is_file():
                continue
            try:
                findings = self.analyze_file(path, context)
                all_findings.extend(findings)
                files_analyzed += 1
            except Exception as e:
                return ExtensionExecutionResult(
                    success=False,
                    findings=all_findings,
                    metrics={"files_analyzed": files_analyzed},
                    error_message=f"Error analyzing '{path}': {e}",
                )

        return ExtensionExecutionResult(
            success=True,
            findings=all_findings,
            metrics={"files_analyzed": files_analyzed, "total_findings": len(all_findings)},
        )
