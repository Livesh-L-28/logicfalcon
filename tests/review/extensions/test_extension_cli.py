"""Unit and integration tests for LogicFalcon extension CLI commands (Phase 4)."""

import json
from pathlib import Path

import pytest
import yaml

from logicfalcon.cli import run_main
from packages.review.extensions.cli import run_extension_cli
from packages.review.extensions.manager import ExtensionManager
from packages.review.extensions.registry import ExtensionRegistry


@pytest.fixture
def cli_manager(tmp_path: Path) -> ExtensionManager:
    user_dir = tmp_path / "user_exts"
    workspace_dir = tmp_path / "workspace_exts"
    registry = ExtensionRegistry()
    return ExtensionManager(
        user_dir=user_dir,
        workspace_dir=workspace_dir,
        registry=registry,
    )


def create_sample_pkg(
    target_dir: Path,
    ext_id: str = "org.acme.perf-rules",
    version: str = "1.0.0",
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0.0",
        "id": ext_id,
        "name": "ACME Performance Rules",
        "version": version,
        "description": "Rules for performance checking",
        "author": "ACME Corp",
        "license": "Apache-2.0",
        "capabilities": [{"capability": "project:read"}],
    }
    (target_dir / "extension.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (target_dir / "plugin.py").write_text("# plugin code", encoding="utf-8")
    return target_dir


def test_cli_list_empty(cli_manager: ExtensionManager, capsys: pytest.CaptureFixture[str]) -> None:
    code = run_extension_cli(["list"], manager=cli_manager)
    assert code == 0
    captured = capsys.readouterr()
    assert "No extensions installed" in captured.out


def test_cli_install_dry_run_and_actual(cli_manager: ExtensionManager, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pkg_dir = create_sample_pkg(tmp_path / "sample_pkg", "org.acme.perf-rules", "1.0.0")

    # 1. Dry run
    code = run_extension_cli(["install", str(pkg_dir), "--dry-run", "--json"], manager=cli_manager)
    assert code == 0
    captured = capsys.readouterr()
    plan_data = json.loads(captured.out)
    assert plan_data["extension_id"] == "org.acme.perf-rules"
    assert plan_data["dry_run"] is True
    assert not (cli_manager.user_dir / "org.acme.perf-rules").exists()

    # 2. Actual install
    code = run_extension_cli(["install", str(pkg_dir), "--json"], manager=cli_manager)
    assert code == 0
    captured = capsys.readouterr()
    install_data = json.loads(captured.out)
    assert install_data["extension_id"] == "org.acme.perf-rules"
    assert (cli_manager.user_dir / "org.acme.perf-rules").exists()


def test_cli_lifecycle_commands(cli_manager: ExtensionManager, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pkg_dir = create_sample_pkg(tmp_path / "sample_pkg", "org.acme.perf-rules", "1.0.0")
    run_extension_cli(["install", str(pkg_dir)], manager=cli_manager)
    capsys.readouterr()  # clear buffer

    # Enable
    code = run_extension_cli(["enable", "org.acme.perf-rules"], manager=cli_manager)
    assert code == 0
    assert "enabled successfully" in capsys.readouterr().out

    # Inspect
    code = run_extension_cli(["inspect", "org.acme.perf-rules", "--json"], manager=cli_manager)
    assert code == 0
    inspect_data = json.loads(capsys.readouterr().out)
    assert inspect_data["manifest"]["id"] == "org.acme.perf-rules"
    assert inspect_data["state"]["enabled"] is True

    # Disable
    code = run_extension_cli(["disable", "org.acme.perf-rules"], manager=cli_manager)
    assert code == 0
    assert "disabled successfully" in capsys.readouterr().out

    # Doctor
    code = run_extension_cli(["doctor", "--json"], manager=cli_manager)
    assert code == 0
    doctor_data = json.loads(capsys.readouterr().out)
    assert len(doctor_data) == 1
    assert doctor_data[0]["healthy"] is True

    # Search
    code = run_extension_cli(["search", "performance", "--json"], manager=cli_manager)
    assert code == 0
    search_data = json.loads(capsys.readouterr().out)
    assert len(search_data) == 1
    assert search_data[0]["id"] == "org.acme.perf-rules"

    # Uninstall
    code = run_extension_cli(["uninstall", "org.acme.perf-rules"], manager=cli_manager)
    assert code == 0
    assert "uninstalled successfully" in capsys.readouterr().out


def test_cli_validate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pkg_dir = create_sample_pkg(tmp_path / "sample_pkg", "org.acme.perf-rules", "1.0.0")
    code = run_extension_cli(["validate", str(pkg_dir), "--json"])
    assert code == 0
    val_data = json.loads(capsys.readouterr().out)
    assert val_data["valid"] is True
    assert val_data["id"] == "org.acme.perf-rules"
    assert val_data["compatible"] is True


def test_logicfalcon_cli_routing_and_backward_compatibility(capsys: pytest.CaptureFixture[str]) -> None:
    # 1. Test extension help via root CLI
    code = run_main(["extension", "--help"])
    assert code == 0
    captured = capsys.readouterr()
    assert "logicfalcon extension" in captured.out

    # 2. Test root CLI --version regression
    code = run_main(["--version"])
    assert code == 0
    captured = capsys.readouterr()
    assert "LogicFalcon 0.1.5" in captured.out

    # 3. Test root CLI doctor regression
    code = run_main(["doctor", "--format", "json"])
    assert code == 0
    captured = capsys.readouterr()
    doc_json = json.loads(captured.out)
    assert doc_json["product"] == "LogicFalcon"
