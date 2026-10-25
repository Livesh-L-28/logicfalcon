# Developer Guide & SDK

This guide explains how to author, test, and package custom LogicFalcon extensions.

---

## 1. Scaffolding a New Extension

You can scaffold a clean extension project using `packages.review.extensions.scaffolding`:

```python
from packages.review.extensions.scaffolding import generate_extension_scaffold

generate_extension_scaffold(
    target_dir="./my-custom-rules",
    extension_id="com.myorg.security-rules",
    name="Security Rules",
    description="Detects sensitive patterns in code",
)
```

This creates:
```
my-custom-rules/
├── extension.yaml
├── README.md
├── src/
│   ├── __init__.py
│   └── analyzer.py
└── tests/
    ├── __init__.py
    └── test_analyzer.py
```

---

## 2. Implementing `StaticAnalysisExtension`

In `src/analyzer.py`, subclass `StaticAnalysisExtension`:

```python
from pathlib import Path
from packages.review.extensions.base import (
    ExtensionExecutionContext,
    ExtensionFinding,
    StaticAnalysisExtension,
)

class MyCustomAnalyzer(StaticAnalysisExtension):
    """Custom static rule implementation."""

    def analyze_file(self, file_path: Path, context: ExtensionExecutionContext) -> list[ExtensionFinding]:
        findings = []
        if file_path.suffix != ".py":
            return findings

        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if "eval(" in line:
                findings.append(
                    ExtensionFinding(
                        rule_id="SEC-001",
                        title="Dangerous eval() Call Detected",
                        message="Use of built-in eval() introduces code injection vulnerabilities.",
                        file_path=str(file_path),
                        start_line=lineno,
                        severity="WARNING",
                        suggestion="Refactor using ast.literal_eval() or explicit parsers.",
                    )
                )
        return findings
```

---

## 3. Testing Locally

Use pytest to test the extension logic in isolation:

```python
from pathlib import Path
from packages.review.extensions.base import ExtensionExecutionContext
from src.analyzer import MyCustomAnalyzer

def test_detects_eval(tmp_path: Path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("eval('2 + 2')\n")

    analyzer = MyCustomAnalyzer()
    ctx = ExtensionExecutionContext(
        extension_id="com.myorg.security-rules",
        workspace_root=tmp_path,
    )
    findings = analyzer.analyze_file(test_file, ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "SEC-001"
```

---

## 4. Installing and Testing in LogicFalcon

```bash
# Validate manifest syntax
logicfalcon extension validate ./my-custom-rules

# Perform dry run
logicfalcon extension install ./my-custom-rules --workspace --dry-run

# Install and enable
logicfalcon extension install ./my-custom-rules --workspace
logicfalcon extension enable com.myorg.security-rules

# Check diagnostics
logicfalcon extension doctor
```
