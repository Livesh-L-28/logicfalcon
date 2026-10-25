"""Scaffolding generator for creating new LogicFalcon extensions."""

from pathlib import Path

import yaml


def generate_extension_scaffold(
    target_dir: Path | str,
    extension_id: str = "com.example.custom-rules",
    name: str = "Custom Rules",
    description: str = "Custom code review rules for LogicFalcon",
    author: str = "LogicFalcon Developer",
    license_type: str = "Apache-2.0",
) -> Path:
    """Generates a complete, ready-to-run LogicFalcon extension project structure."""
    out_dir = Path(target_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    src_dir = out_dir / "src"
    src_dir.mkdir(exist_ok=True)
    tests_dir = out_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    # 1. Manifest
    manifest_data = {
        "schema_version": "1.0.0",
        "id": extension_id,
        "name": name,
        "version": "0.1.0",
        "description": description,
        "author": author,
        "license": license_type,
        "compatibility": {
            "logicfalcon": ">=0.1.4",
            "python": ">=3.12",
        },
        "capabilities": [
            {
                "capability": "project:read",
                "description": "Read project source files for inspection",
            },
            {
                "capability": "project:analyze",
                "description": "Parse AST and analyze code constructs",
            },
        ],
        "entry_points": {
            "analyzer": [
                {
                    "name": "default",
                    "target": "src.analyzer:CustomRuleExtension",
                    "execution_mode": "in_process",
                }
            ]
        },
        "configuration_schema": {
            "type": "object",
            "properties": {
                "max_warnings": {"type": "integer", "default": 50},
            },
        },
    }
    (out_dir / "extension.yaml").write_text(yaml.safe_dump(manifest_data, sort_keys=False), encoding="utf-8")

    # 2. Source code
    analyzer_code = '''"""Custom LogicFalcon Static Analysis Extension."""

from pathlib import Path
from packages.review.extensions.base import (
    ExtensionExecutionContext,
    ExtensionFinding,
    StaticAnalysisExtension,
)


class CustomRuleExtension(StaticAnalysisExtension):
    """Inspects files and reports findings."""

    def analyze_file(self, file_path: Path, context: ExtensionExecutionContext) -> list[ExtensionFinding]:
        findings: list[ExtensionFinding] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return findings

        for lineno, line in enumerate(content.splitlines(), start=1):
            if "# HACK" in line:
                findings.append(
                    ExtensionFinding(
                        rule_id="RULE-001",
                        title="Unresolved HACK Marker",
                        message="Temporary workaround comment detected.",
                        file_path=str(file_path),
                        start_line=lineno,
                        severity="WARNING",
                        suggestion="Refactor the code to eliminate temporary workarounds.",
                    )
                )
        return findings
'''
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "analyzer.py").write_text(analyzer_code, encoding="utf-8")

    # 3. Test code
    test_code = f'''"""Tests for {name}."""

from pathlib import Path
from packages.review.extensions.base import ExtensionExecutionContext
from src.analyzer import CustomRuleExtension


def test_analyzer_detects_marker(tmp_path: Path) -> None:
    test_file = tmp_path / "sample.py"
    test_file.write_text("# HACK: fix later\\nprint(1)\\n", encoding="utf-8")

    ext = CustomRuleExtension()
    ctx = ExtensionExecutionContext(
        extension_id="{extension_id}",
        workspace_root=tmp_path,
    )
    findings = ext.analyze_file(test_file, ctx)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-001"
    assert findings[0].start_line == 1
'''
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_analyzer.py").write_text(test_code, encoding="utf-8")

    # 4. README.md
    readme_content = f"""# {name}

{description}

## Installation

```bash
logicfalcon extension install .
logicfalcon extension enable {extension_id}
```

## Running Tests

```bash
pytest tests/
```
"""
    (out_dir / "README.md").write_text(readme_content, encoding="utf-8")

    return out_dir
