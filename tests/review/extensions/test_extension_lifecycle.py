"""Comprehensive unit tests for the LogicFalcon Extension Lifecycle Manager (Phase 2)."""

import json
from pathlib import Path

import pytest
import yaml

from packages.review.extensions.errors import (
    ExtensionError,
)
from packages.review.extensions.manager import ExtensionManager
from packages.review.extensions.models import (
    ExtensionLifecycleState,
    ExtensionStorageScope,
)
from packages.review.extensions.registry import ExtensionRegistry


@pytest.fixture
def isolated_manager(tmp_path: Path) -> ExtensionManager:
    user_dir = tmp_path / "user_extensions"
    workspace_dir = tmp_path / "workspace_extensions"
    registry = ExtensionRegistry()
    return ExtensionManager(
        user_dir=user_dir,
        workspace_dir=workspace_dir,
        registry=registry,
    )


def create_mock_extension(
    dir_path: Path,
    ext_id: str = "com.acme.perf-rules",
    version: str = "1.0.0",
    min_core: str = ">=0.1.0",
    capabilities: list[str] | None = None,
) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    caps = [{"capability": c, "description": f"Need {c}"} for c in (capabilities or ["project:read"])]
    manifest_data = {
        "manifest_version": "1.0.0",
        "id": ext_id,
        "name": "ACME Performance Rules",
        "version": version,
        "description": "Custom AST rules",
        "publisher": {"name": "ACME Corp", "email": "dev@acme.com"},
        "compatibility": {"logicfalcon": min_core},
        "entry_point": {"module": "rules", "attribute": "extension"},
        "capabilities": caps,
    }
    manifest_file = dir_path / "extension.yaml"
    manifest_file.write_text(yaml.safe_dump(manifest_data), encoding="utf-8")
    (dir_path / "rules.py").write_text("# mock rules", encoding="utf-8")
    return dir_path


def test_plan_install_dry_run(isolated_manager: ExtensionManager, tmp_path: Path) -> None:
    src_dir = create_mock_extension(tmp_path / "pkg_src", ext_id="com.acme.perf-rules", version="1.0.0")

    # Dry run planning should NOT mutate the destination directory
    plan = isolated_manager.plan_install(src_dir, scope=ExtensionStorageScope.USER)

    assert plan.extension_id == "com.acme.perf-rules"
    assert plan.version == "1.0.0"
    assert plan.target_scope == ExtensionStorageScope.USER
    assert plan.is_compatible is True
    assert "project:read" in plan.requested_capabilities
    assert not plan.destination_path.exists()

    # Dry run through install() method
    install_plan = isolated_manager.install(src_dir, scope=ExtensionStorageScope.USER, dry_run=True)
    assert install_plan.extension_id == "com.acme.perf-rules"
    assert not install_plan.destination_path.exists()


def test_install_and_lifecycle_transitions(isolated_manager: ExtensionManager, tmp_path: Path) -> None:
    src_dir = create_mock_extension(tmp_path / "pkg_src", ext_id="com.acme.perf-rules", version="1.0.0")

    # 1. Install
    plan = isolated_manager.install(src_dir, scope=ExtensionStorageScope.USER, dry_run=False)
    assert plan.destination_path.exists()
    assert (plan.destination_path / "rules.py").exists()

    entry = isolated_manager.registry.get("com.acme.perf-rules")
    assert entry is not None
    assert entry.state.state == ExtensionLifecycleState.INSTALLED
    assert entry.state.enabled is False

    # Verify atomic state file was written
    state_file = isolated_manager.user_dir / "state.json"
    assert state_file.is_file()
    state_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert "com.acme.perf-rules" in state_data
    assert state_data["com.acme.perf-rules"]["enabled"] is False

    # 2. Enable
    enabled_state = isolated_manager.enable("com.acme.perf-rules")
    assert enabled_state.enabled is True
    assert enabled_state.state == ExtensionLifecycleState.ENABLED
    assert entry.state.enabled is True

    # 3. Disable
    disabled_state = isolated_manager.disable("com.acme.perf-rules")
    assert disabled_state.enabled is False
    assert disabled_state.state == ExtensionLifecycleState.DISABLED
    assert entry.state.enabled is False


def test_install_incompatible_rejected(isolated_manager: ExtensionManager, tmp_path: Path) -> None:
    src_dir = create_mock_extension(
        tmp_path / "pkg_incompat",
        ext_id="com.acme.future-extension",
        version="2.0.0",
        min_core=">=99.0.0",
    )

    with pytest.raises(ExtensionError, match="Cannot install incompatible extension"):
        isolated_manager.install(src_dir, scope=ExtensionStorageScope.USER)


def test_update_and_rollback(isolated_manager: ExtensionManager, tmp_path: Path) -> None:
    src_v1 = create_mock_extension(tmp_path / "pkg_v1", ext_id="com.acme.perf-rules", version="1.0.0")
    src_v2 = create_mock_extension(tmp_path / "pkg_v2", ext_id="com.acme.perf-rules", version="1.1.0")

    isolated_manager.install(src_v1, scope=ExtensionStorageScope.USER)
    isolated_manager.enable("com.acme.perf-rules")

    entry = isolated_manager.registry.get("com.acme.perf-rules")
    assert entry.manifest.version == "1.0.0"
    assert entry.state.enabled is True

    # Update to v2
    update_plan = isolated_manager.update("com.acme.perf-rules", src_v2)
    assert update_plan.version == "1.1.0"

    entry_v2 = isolated_manager.registry.get("com.acme.perf-rules")
    assert entry_v2.manifest.version == "1.1.0"
    assert entry_v2.state.enabled is True  # Preserved enabled state

    # Roll back to v1
    rollback_state = isolated_manager.rollback("com.acme.perf-rules")
    assert rollback_state.version == "1.0.0"
    entry_restored = isolated_manager.registry.get("com.acme.perf-rules")
    assert entry_restored.manifest.version == "1.0.0"


def test_uninstall_preserve_and_purge_config(isolated_manager: ExtensionManager, tmp_path: Path) -> None:
    src_dir = create_mock_extension(tmp_path / "pkg_src", ext_id="com.acme.perf-rules", version="1.0.0")
    isolated_manager.install(src_dir, scope=ExtensionStorageScope.USER)

    # 1. Default uninstall preserves configuration/history in state.json
    isolated_manager.uninstall("com.acme.perf-rules", purge_config=False)
    assert isolated_manager.registry.get("com.acme.perf-rules") is None
    assert not (isolated_manager.user_dir / "com.acme.perf-rules").exists()

    state_file = isolated_manager.user_dir / "state.json"
    state_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert "com.acme.perf-rules" in state_data
    assert state_data["com.acme.perf-rules"]["state"] == "not_installed"

    # Reinstall and uninstall with purge_config=True
    isolated_manager.install(src_dir, scope=ExtensionStorageScope.USER)
    isolated_manager.uninstall("com.acme.perf-rules", purge_config=True)

    state_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert "com.acme.perf-rules" not in state_data


def test_scope_precedence_workspace_over_user(isolated_manager: ExtensionManager, tmp_path: Path) -> None:
    src_user = create_mock_extension(tmp_path / "pkg_user", ext_id="com.acme.perf-rules", version="1.0.0")
    src_ws = create_mock_extension(tmp_path / "pkg_ws", ext_id="com.acme.perf-rules", version="1.5.0")

    isolated_manager.install(src_user, scope=ExtensionStorageScope.USER)
    isolated_manager.install(src_ws, scope=ExtensionStorageScope.WORKSPACE)

    # Re-discover
    discovered = isolated_manager.discover()
    assert len(discovered) == 1
    manifest, state = discovered[0]
    assert manifest.id == "com.acme.perf-rules"
    # Workspace should override user scope
    assert manifest.version == "1.5.0"
    assert state.scope == ExtensionStorageScope.WORKSPACE


def test_diagnose(isolated_manager: ExtensionManager, tmp_path: Path) -> None:
    src_dir = create_mock_extension(tmp_path / "pkg_src", ext_id="com.acme.perf-rules", version="1.0.0")
    isolated_manager.install(src_dir, scope=ExtensionStorageScope.USER)

    reports = isolated_manager.diagnose()
    assert len(reports) == 1
    report = reports[0]
    assert report.extension_id == "com.acme.perf-rules"
    assert report.healthy is True
    assert len(report.checks) >= 2
    assert all(c["passed"] for c in report.checks)
