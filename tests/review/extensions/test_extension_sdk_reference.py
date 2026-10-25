"""Tests for Developer SDK, Scaffolding, and Reference Extension (Phase 5)."""

from pathlib import Path

from logicfalcon.sdk import (
    diagnose_extensions,
    disable_extension,
    enable_extension,
    get_extension,
    install_extension,
    list_extensions,
    uninstall_extension,
)
from packages.review.extensions.base import ExtensionExecutionContext
from packages.review.extensions.manifest import parse_manifest
from packages.review.extensions.reference.todo_counter.analyzer import TodoAnalyzerExtension
from packages.review.extensions.scaffolding import generate_extension_scaffold


def test_scaffolding_generator(tmp_path: Path) -> None:
    target_dir = tmp_path / "new_extension"
    generated_path = generate_extension_scaffold(
        target_dir=target_dir,
        extension_id="org.myteam.security-check",
        name="Security Checker",
        description="Checks for custom security rules",
    )

    assert generated_path.is_dir()
    manifest_file = generated_path / "extension.yaml"
    assert manifest_file.is_file()

    # Validate generated manifest passes strict parser
    manifest = parse_manifest(manifest_file)
    assert manifest.id == "org.myteam.security-check"
    assert manifest.name == "Security Checker"
    assert len(manifest.capabilities) == 2

    # Check generated files
    assert (generated_path / "src" / "analyzer.py").is_file()
    assert (generated_path / "tests" / "test_analyzer.py").is_file()
    assert (generated_path / "README.md").is_file()


def test_reference_todo_analyzer(tmp_path: Path) -> None:
    ref_dir = Path(__file__).parent.parent.parent.parent / "packages" / "review" / "extensions" / "reference" / "todo_counter"
    manifest_file = ref_dir / "extension.yaml"
    assert manifest_file.is_file()

    manifest = parse_manifest(manifest_file)
    assert manifest.id == "org.logicfalcon.todo-analyzer"

    # Create sample file with technical debt markers
    sample_file = tmp_path / "sample_code.py"
    sample_content = (
        "def compute_score():\n"
        "    # TODO: implement caching algorithm\n"
        "    x = 10\n"
        "    # FIXME: check for division by zero\n"
        "    return x / 2\n"
    )
    sample_file.write_text(sample_content, encoding="utf-8")

    analyzer = TodoAnalyzerExtension(manifest=manifest)
    ctx = ExtensionExecutionContext(
        extension_id=manifest.id,
        workspace_root=tmp_path,
    )

    findings = analyzer.analyze_file(sample_file, ctx)
    assert len(findings) == 2

    # Check TODO finding
    todo_finding = next(f for f in findings if f.rule_id == "DEBT-TODO")
    assert todo_finding.start_line == 2
    assert todo_finding.severity == "INFO"
    assert "caching algorithm" in todo_finding.message

    # Check FIXME finding
    fixme_finding = next(f for f in findings if f.rule_id == "DEBT-FIXME")
    assert fixme_finding.start_line == 4
    assert fixme_finding.severity == "WARNING"
    assert "division by zero" in fixme_finding.message

    # Test clean file produces 0 findings
    clean_file = tmp_path / "clean_code.py"
    clean_file.write_text("def add(a, b): return a + b\n", encoding="utf-8")
    assert len(analyzer.analyze_file(clean_file, ctx)) == 0


def test_programmatic_sdk_extension_lifecycle(tmp_path: Path) -> None:
    user_ext_dir = tmp_path / "user_exts"
    ws_ext_dir = tmp_path / "ws_exts"

    ref_dir = Path(__file__).parent.parent.parent.parent / "packages" / "review" / "extensions" / "reference" / "todo_counter"

    # 1. Install via SDK
    plan = install_extension(
        source=ref_dir,
        workspace=False,
        dry_run=False,
        user_dir=user_ext_dir,
        workspace_dir=ws_ext_dir,
    )
    assert plan.extension_id == "org.logicfalcon.todo-analyzer"

    # 2. List & Get
    exts = list_extensions(user_dir=user_ext_dir, workspace_dir=ws_ext_dir)
    assert len(exts) == 1
    assert exts[0][0].id == "org.logicfalcon.todo-analyzer"

    meta = get_extension("org.logicfalcon.todo-analyzer", user_dir=user_ext_dir, workspace_dir=ws_ext_dir)
    assert meta is not None
    assert meta.name == "TODO & Debt Analyzer"

    # 3. Enable
    state = enable_extension("org.logicfalcon.todo-analyzer", user_dir=user_ext_dir, workspace_dir=ws_ext_dir)
    assert state.enabled is True

    # 4. Diagnose
    reports = diagnose_extensions(user_dir=user_ext_dir, workspace_dir=ws_ext_dir)
    assert len(reports) == 1
    assert reports[0].healthy is True

    # 5. Disable
    state = disable_extension("org.logicfalcon.todo-analyzer", user_dir=user_ext_dir, workspace_dir=ws_ext_dir)
    assert state.enabled is False

    # 6. Uninstall
    uninstall_extension("org.logicfalcon.todo-analyzer", purge_config=True, user_dir=user_ext_dir, workspace_dir=ws_ext_dir)
    assert get_extension("org.logicfalcon.todo-analyzer", user_dir=user_ext_dir, workspace_dir=ws_ext_dir) is None
