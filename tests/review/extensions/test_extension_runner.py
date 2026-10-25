"""Tests for Extension Runner, Subprocess Worker Isolation, and Reliability (Phase 6)."""

from pathlib import Path
from typing import Any

import pytest

from packages.review.extensions.base import ExtensionExecutionContext
from packages.review.extensions.errors import (
    ExtensionExecutionError,
    WorkerCrashError,
)
from packages.review.extensions.manifest import parse_manifest
from packages.review.extensions.models import ExecutionMode
from packages.review.extensions.runner import ExtensionRunner


@pytest.fixture
def ref_manifest_and_path() -> tuple[Any, Path]:
    ref_dir = Path(__file__).parent.parent.parent.parent / "packages" / "review" / "extensions" / "reference" / "todo_counter"
    manifest = parse_manifest(ref_dir / "extension.yaml")
    return manifest, ref_dir


def test_in_process_execution(ref_manifest_and_path: tuple[Any, Path], tmp_path: Path) -> None:
    manifest, ref_dir = ref_manifest_and_path
    runner = ExtensionRunner()

    target_file = tmp_path / "test_file.py"
    target_file.write_text("# TODO: write test cases\nx = 1\n", encoding="utf-8")

    ctx = ExtensionExecutionContext(
        extension_id=manifest.id,
        workspace_root=tmp_path,
    )

    result = runner.execute(
        manifest=manifest,
        installed_path=ref_dir,
        target_files=[target_file],
        context=ctx,
        force_mode=ExecutionMode.IN_PROCESS,
    )

    assert result.success is True
    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "DEBT-TODO"
    assert "write test cases" in result.findings[0].message


def test_subprocess_worker_execution(ref_manifest_and_path: tuple[Any, Path], tmp_path: Path) -> None:
    manifest, ref_dir = ref_manifest_and_path
    runner = ExtensionRunner()

    target_file = tmp_path / "test_worker.py"
    target_file.write_text("# FIXME: resolve deadlock in queue\ny = 2\n", encoding="utf-8")

    ctx = ExtensionExecutionContext(
        extension_id=manifest.id,
        workspace_root=tmp_path,
    )

    result = runner.execute(
        manifest=manifest,
        installed_path=ref_dir,
        target_files=[target_file],
        context=ctx,
        force_mode=ExecutionMode.SUBPROCESS_WORKER,
        timeout_seconds=15.0,
    )

    assert result.success is True
    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "DEBT-FIXME"
    assert "resolve deadlock" in result.findings[0].message


def test_worker_crash_handling(tmp_path: Path) -> None:
    # Create crashing extension
    crash_dir = tmp_path / "crashing_ext"
    crash_dir.mkdir()
    manifest_yaml = (
        'schema_version: "1.0.0"\n'
        'id: "org.test.crashing-ext"\n'
        'name: "Crashing Ext"\n'
        'version: "1.0.0"\n'
        'entry_points:\n'
        '  analyzer:\n'
        '    - name: "crash"\n'
        '      target: "crash_plugin:CrashingExtension"\n'
        '      execution_mode: "subprocess_worker"\n'
    )
    (crash_dir / "extension.yaml").write_text(manifest_yaml, encoding="utf-8")
    (crash_dir / "crash_plugin.py").write_text(
        "import sys\n"
        "from packages.review.extensions.base import BaseExtension\n"
        "class CrashingExtension(BaseExtension):\n"
        "    def execute(self, files, ctx):\n"
        "        sys.exit(42)\n",
        encoding="utf-8",
    )

    manifest = parse_manifest(crash_dir / "extension.yaml")
    runner = ExtensionRunner()
    ctx = ExtensionExecutionContext(extension_id=manifest.id, workspace_root=tmp_path)

    with pytest.raises(WorkerCrashError, match="Extension worker crashed with exit code 42"):
        runner.execute(
            manifest=manifest,
            installed_path=crash_dir,
            target_files=[],
            context=ctx,
            force_mode=ExecutionMode.SUBPROCESS_WORKER,
        )


def test_worker_timeout_enforcement(tmp_path: Path) -> None:
    # Create hanging extension
    hang_dir = tmp_path / "hanging_ext"
    hang_dir.mkdir()
    manifest_yaml = (
        'schema_version: "1.0.0"\n'
        'id: "org.test.hanging-ext"\n'
        'name: "Hanging Ext"\n'
        'version: "1.0.0"\n'
        'entry_points:\n'
        '  analyzer:\n'
        '    - name: "hang"\n'
        '      target: "hang_plugin:HangingExtension"\n'
        '      execution_mode: "subprocess_worker"\n'
    )
    (hang_dir / "extension.yaml").write_text(manifest_yaml, encoding="utf-8")
    (hang_dir / "hang_plugin.py").write_text(
        "import time\n"
        "from packages.review.extensions.base import BaseExtension\n"
        "class HangingExtension(BaseExtension):\n"
        "    def execute(self, files, ctx):\n"
        "        time.sleep(10)\n",
        encoding="utf-8",
    )

    manifest = parse_manifest(hang_dir / "extension.yaml")
    runner = ExtensionRunner()
    ctx = ExtensionExecutionContext(extension_id=manifest.id, workspace_root=tmp_path)

    # 1.0 second timeout should cleanly terminate hanging worker
    with pytest.raises(ExtensionExecutionError, match=r"timed out after 1\.0 seconds"):
        runner.execute(
            manifest=manifest,
            installed_path=hang_dir,
            target_files=[],
            context=ctx,
            force_mode=ExecutionMode.SUBPROCESS_WORKER,
            timeout_seconds=1.0,
        )
