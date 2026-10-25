"""Reference extension implementing deterministic TODO, FIXME, and technical debt inspection."""

import io
import re
import tokenize
from pathlib import Path

from packages.review.extensions.base import (
    ExtensionExecutionContext,
    ExtensionFinding,
    StaticAnalysisExtension,
)

DEBT_PATTERN = re.compile(r"#\s*(TODO|FIXME|XXX|BUG)\b[:\s]*(.*)", re.IGNORECASE)


class TodoAnalyzerExtension(StaticAnalysisExtension):
    """Inspects Python source code for technical debt comments and unresolved markers."""

    def analyze_file(self, file_path: Path, context: ExtensionExecutionContext) -> list[ExtensionFinding]:
        findings: list[ExtensionFinding] = []
        if file_path.suffix not in (".py", ".pyi"):
            return findings

        try:
            raw_bytes = file_path.read_bytes()
        except Exception:
            return findings

        try:
            tokens = tokenize.tokenize(io.BytesIO(raw_bytes).readline)
            for tok_type, tok_string, (srow, _scol), (erow, _ecol), _line in tokens:
                if tok_type == tokenize.COMMENT:
                    match = DEBT_PATTERN.search(tok_string)
                    if match:
                        marker = match.group(1).upper()
                        comment_body = match.group(2).strip()
                        severity = "WARNING" if marker in ("FIXME", "BUG") else "INFO"
                        findings.append(
                            ExtensionFinding(
                                rule_id=f"DEBT-{marker}",
                                title=f"Unresolved {marker} Comment",
                                message=f"Identified '{marker}' marker: {comment_body or 'No explanation provided'}",
                                file_path=str(file_path),
                                start_line=srow,
                                end_line=erow,
                                severity=severity,
                                suggestion=f"Address or track the technical debt identified by {marker} before production release.",
                                data={"marker": marker, "details": comment_body},
                            )
                        )
        except Exception:
            # Fallback line-by-line scanning if tokenize fails
            try:
                lines = raw_bytes.decode("utf-8", errors="ignore").splitlines()
                for lineno, line in enumerate(lines, start=1):
                    match = DEBT_PATTERN.search(line)
                    if match:
                        marker = match.group(1).upper()
                        comment_body = match.group(2).strip()
                        severity = "WARNING" if marker in ("FIXME", "BUG") else "INFO"
                        findings.append(
                            ExtensionFinding(
                                rule_id=f"DEBT-{marker}",
                                title=f"Unresolved {marker} Comment",
                                message=f"Identified '{marker}' marker: {comment_body or 'No explanation provided'}",
                                file_path=str(file_path),
                                start_line=lineno,
                                end_line=lineno,
                                severity=severity,
                                suggestion=f"Address or track the technical debt identified by {marker}.",
                                data={"marker": marker, "details": comment_body},
                            )
                        )
            except Exception:
                pass

        return findings
