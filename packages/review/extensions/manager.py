"""Lifecycle manager for discovering, installing, configuring, and updating LogicFalcon extensions."""

import contextlib
import json
import os
import shutil
import tempfile
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore

from packages.review.extensions.compatibility import assert_compatible, check_compatibility
from packages.review.extensions.errors import (
    ExtensionError,
    ExtensionNotFoundError,
    LockContentionError,
    ManifestValidationError,
)
from packages.review.extensions.manifest import parse_manifest
from packages.review.extensions.models import (
    ExtensionHealthReport,
    ExtensionLifecycleState,
    ExtensionManifest,
    ExtensionStateRecord,
    ExtensionStorageScope,
)
from packages.review.extensions.registry import ExtensionRegistry, global_extension_registry

_local = threading.local()


@dataclass
class InstallationPlan:
    """Preview plan for installing or updating an extension."""

    extension_id: str
    name: str
    version: str
    target_scope: ExtensionStorageScope
    destination_path: Path
    manifest: ExtensionManifest
    is_compatible: bool
    compatibility_message: str | None
    requested_capabilities: list[str]
    is_update: bool = False
    existing_version: str | None = None


class ExtensionManager:
    """Manages the full lifecycle of LogicFalcon extensions (user and workspace scopes)."""

    def __init__(
        self,
        user_dir: Path | None = None,
        workspace_dir: Path | None = None,
        registry: ExtensionRegistry | None = None,
    ) -> None:
        self.user_dir = user_dir or (Path.home() / ".logicfalcon" / "extensions")
        self.workspace_dir = workspace_dir or (Path(".logicfalcon") / "extensions")
        self.registry = registry or global_extension_registry

    def get_scope_dir(self, scope: ExtensionStorageScope) -> Path:
        """Resolves root storage directory for a specific scope."""
        if scope == ExtensionStorageScope.WORKSPACE:
            return self.workspace_dir
        return self.user_dir

    def _state_file_path(self, scope: ExtensionStorageScope) -> Path:
        return self.get_scope_dir(scope) / "state.json"

    def _load_state_dict(self, scope: ExtensionStorageScope) -> dict[str, ExtensionStateRecord]:
        """Loads persisted state records for a scope."""
        state_file = self._state_file_path(scope)
        if not state_file.is_file():
            return {}
        try:
            raw = json.loads(state_file.read_text(encoding="utf-8"))
            records = {}
            for k, v in raw.items():
                records[k.lower()] = ExtensionStateRecord.model_validate(v)
            return records
        except Exception:
            return {}

    def _save_state_dict(self, scope: ExtensionStorageScope, records: dict[str, ExtensionStateRecord]) -> None:
        """Atomically saves state records to disk."""
        scope_dir = self.get_scope_dir(scope)
        scope_dir.mkdir(parents=True, exist_ok=True)
        state_file = self._state_file_path(scope)

        data = {k: v.model_dump(mode="json") for k, v in records.items()}
        tmp_file = state_file.with_suffix(".tmp")
        try:
            tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            # Enforce 0o600 permissions
            os.chmod(tmp_file, 0o600)
            tmp_file.replace(state_file)
        finally:
            if tmp_file.exists():
                with contextlib.suppress(Exception):
                    tmp_file.unlink()

    @contextlib.contextmanager
    def scope_lock(self, scope: ExtensionStorageScope, timeout: float = 10.0) -> Generator[None, None, None]:
        """Acquires an advisory inter-process exclusive lock on the scope directory.

        Re-entrant within the same thread. Blocks concurrent processes or threads
        attempting conflicting lifecycle operations on the same scope until released
        or timeout expires.
        """
        scope_dir = self.get_scope_dir(scope)
        scope_dir.mkdir(parents=True, exist_ok=True)
        lock_file = scope_dir / ".lock"
        canonical_key = str(lock_file.resolve())

        if not hasattr(_local, "held_locks"):
            _local.held_locks = {}

        if canonical_key in _local.held_locks:
            _local.held_locks[canonical_key]["depth"] += 1
            try:
                yield
            finally:
                _local.held_locks[canonical_key]["depth"] -= 1
                if _local.held_locks[canonical_key]["depth"] <= 0:
                    del _local.held_locks[canonical_key]
            return

        # Open lock file with 0o600 permissions
        fd = os.open(str(lock_file), os.O_RDWR | os.O_CREAT, 0o600)
        with contextlib.suppress(OSError):
            os.chmod(str(lock_file), 0o600)

        acquired = False
        if fcntl is not None:
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except (BlockingIOError, OSError):
                    if time.monotonic() >= deadline:
                        break
                    time.sleep(0.05)
        else:
            acquired = True

        if not acquired:
            os.close(fd)
            raise LockContentionError(
                f"Timed out after {timeout:.1f}s waiting for scope lock: {lock_file}. "
                "Another process or operation is actively modifying extensions in this scope.",
                scope=scope.value,
                lock_path=str(lock_file),
            )

        _local.held_locks[canonical_key] = {"fd": fd, "depth": 1}
        try:
            yield
        finally:
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
            finally:
                os.close(fd)
                if canonical_key in _local.held_locks:
                    del _local.held_locks[canonical_key]

    def discover(self) -> list[tuple[ExtensionManifest, ExtensionStateRecord]]:
        """Discovers all installed extensions across workspace and user scopes.

        Workspace scope takes precedence over user scope if the same extension ID exists in both.
        """
        discovered: dict[str, tuple[ExtensionManifest, ExtensionStateRecord]] = {}

        # 1. Inspect user scope first
        for manifest, state in self._scan_scope(ExtensionStorageScope.USER):
            discovered[manifest.id] = (manifest, state)

        # 2. Inspect workspace scope (overriding user scope if duplicate)
        for manifest, state in self._scan_scope(ExtensionStorageScope.WORKSPACE):
            discovered[manifest.id] = (manifest, state)

        # Populate runtime registry
        for manifest, state in discovered.values():
            self.registry.register(manifest, state=state, overwrite=True)

        return sorted(discovered.values(), key=lambda x: x[0].id)

    def _scan_scope(self, scope: ExtensionStorageScope) -> list[tuple[ExtensionManifest, ExtensionStateRecord]]:
        """Scans a single storage scope for valid installed extensions."""
        scope_dir = self.get_scope_dir(scope)
        if not scope_dir.is_dir():
            return []

        state_dict = self._load_state_dict(scope)
        results: list[tuple[ExtensionManifest, ExtensionStateRecord]] = []

        for item in scope_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                manifest_file = item / "extension.yaml"
                if not manifest_file.is_file():
                    manifest_file = item / "extension.json"

                if manifest_file.is_file():
                    try:
                        manifest = parse_manifest(manifest_file)
                        state = state_dict.get(manifest.id)
                        if state is None:
                            state = ExtensionStateRecord(
                                id=manifest.id,
                                version=manifest.version,
                                state=ExtensionLifecycleState.INSTALLED,
                                scope=scope,
                                installed_path=str(item),
                                enabled=False,
                            )
                        results.append((manifest, state))
                    except Exception:
                        continue
        return results

    def plan_install(
        self,
        source_dir_or_manifest: Path | str,
        scope: ExtensionStorageScope = ExtensionStorageScope.USER,
    ) -> InstallationPlan:
        """Inspects and plans installation without mutating filesystem state."""
        src_path = Path(source_dir_or_manifest)
        if src_path.is_file() and src_path.name in ("extension.yaml", "extension.json"):
            manifest = parse_manifest(src_path)
        elif src_path.is_dir():
            manifest_file = src_path / "extension.yaml"
            if not manifest_file.is_file():
                manifest_file = src_path / "extension.json"
            if not manifest_file.is_file():
                raise ManifestValidationError(f"No extension.yaml or extension.json found in {src_path}")
            manifest = parse_manifest(manifest_file)
        else:
            raise ManifestValidationError(f"Invalid extension installation source: {source_dir_or_manifest}")

        is_compat, compat_msg = check_compatibility(manifest)
        dest_dir = self.get_scope_dir(scope) / manifest.id

        state_dict = self._load_state_dict(scope)
        existing = state_dict.get(manifest.id)
        is_update = existing is not None

        return InstallationPlan(
            extension_id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            target_scope=scope,
            destination_path=dest_dir,
            manifest=manifest,
            is_compatible=is_compat,
            compatibility_message=compat_msg,
            requested_capabilities=[c.capability for c in manifest.capabilities],
            is_update=is_update,
            existing_version=existing.version if existing else None,
        )

    def install(
        self,
        source_dir: Path | str,
        scope: ExtensionStorageScope = ExtensionStorageScope.USER,
        dry_run: bool = False,
        lock_timeout: float = 10.0,
    ) -> InstallationPlan:
        """Installs an extension from a source directory into the specified scope."""
        plan = self.plan_install(source_dir, scope=scope)

        if not plan.is_compatible:
            raise ExtensionError(
                f"Cannot install incompatible extension: {plan.compatibility_message}",
                extension_id=plan.extension_id,
            )

        if dry_run:
            return plan

        with self.scope_lock(scope, timeout=lock_timeout):
            src_path = Path(source_dir)
            dest_dir = plan.destination_path
            scope_dir = self.get_scope_dir(scope)
            scope_dir.mkdir(parents=True, exist_ok=True)

            # Atomic installation via staging directory
            staging_dir = Path(tempfile.mkdtemp(prefix=f"ext_{plan.extension_id}_", dir=scope_dir))
            backup_dir = dest_dir.with_suffix(".backup")
            try:
                # Copy all extension assets
                for item in src_path.iterdir():
                    if item.name.startswith("."):
                        continue
                    target = staging_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, target)
                    else:
                        shutil.copy2(item, target)

                # Atomic swap
                if dest_dir.exists():
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir)
                    dest_dir.rename(backup_dir)

                staging_dir.rename(dest_dir)

                # Retain backup_dir as a rollback snapshot
                # If an update succeeds, backup_dir is kept so rollback() can restore it if needed.
            except Exception as e:
                # Restore if update aborted mid-flight
                if backup_dir.exists() and not dest_dir.exists():
                    backup_dir.rename(dest_dir)
                raise ExtensionError(f"Failed to install extension '{plan.extension_id}': {e}", extension_id=plan.extension_id) from e
            finally:
                if staging_dir.exists():
                    with contextlib.suppress(Exception):
                        shutil.rmtree(staging_dir)

            # Update persisted state
            state_dict = self._load_state_dict(scope)
            state_record = ExtensionStateRecord(
                id=plan.extension_id,
                version=plan.version,
                state=ExtensionLifecycleState.INSTALLED,
                scope=scope,
                installed_path=str(dest_dir),
                enabled=False,
                installed_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            state_dict[plan.extension_id] = state_record
            self._save_state_dict(scope, state_dict)

            # Register in active runtime registry
            self.registry.register(plan.manifest, state=state_record, overwrite=True)
            return plan

    def enable(self, extension_id: str, lock_timeout: float = 10.0) -> ExtensionStateRecord:
        """Enables an installed extension."""
        norm_id = extension_id.strip().lower()
        entry = self.registry.get(norm_id)
        if not entry:
            self.discover()
            entry = self.registry.get(norm_id)
        if not entry:
            raise ExtensionNotFoundError(f"Extension '{norm_id}' is not installed.", extension_id=norm_id)

        assert_compatible(entry.manifest)

        scope = entry.state.scope
        with self.scope_lock(scope, timeout=lock_timeout):
            state_dict = self._load_state_dict(scope)
            record = state_dict.get(norm_id, entry.state)

            record.enabled = True
            record.state = ExtensionLifecycleState.ENABLED
            record.updated_at = datetime.now(UTC)
            state_dict[norm_id] = record
            self._save_state_dict(scope, state_dict)

            entry.state = record
            return record

    def disable(self, extension_id: str, lock_timeout: float = 10.0) -> ExtensionStateRecord:
        """Disables an active extension without removing its configuration or files."""
        norm_id = extension_id.strip().lower()
        entry = self.registry.get(norm_id)
        if not entry:
            self.discover()
            entry = self.registry.get(norm_id)
        if not entry:
            raise ExtensionNotFoundError(f"Extension '{norm_id}' is not installed.", extension_id=norm_id)

        scope = entry.state.scope
        with self.scope_lock(scope, timeout=lock_timeout):
            state_dict = self._load_state_dict(scope)
            record = state_dict.get(norm_id, entry.state)

            record.enabled = False
            record.state = ExtensionLifecycleState.DISABLED
            record.updated_at = datetime.now(UTC)
            state_dict[norm_id] = record
            self._save_state_dict(scope, state_dict)

            entry.state = record
            return record

    def update(
        self,
        extension_id: str,
        new_source_dir: Path | str,
        lock_timeout: float = 10.0,
    ) -> InstallationPlan:
        """Updates an extension with automatic rollback on failure."""
        norm_id = extension_id.strip().lower()
        entry = self.registry.get(norm_id)
        if not entry:
            self.discover()
            entry = self.registry.get(norm_id)
        if not entry:
            raise ExtensionNotFoundError(f"Extension '{norm_id}' is not installed.", extension_id=norm_id)

        scope = entry.state.scope
        with self.scope_lock(scope, timeout=lock_timeout):
            was_enabled = entry.state.enabled

            plan = self.install(new_source_dir, scope=scope, dry_run=False, lock_timeout=lock_timeout)
            if was_enabled:
                self.enable(norm_id, lock_timeout=lock_timeout)
            return plan

    def rollback(self, extension_id: str, lock_timeout: float = 10.0) -> ExtensionStateRecord:
        """Rolls back an extension to its prior backup if one exists."""
        norm_id = extension_id.strip().lower()
        entry = self.registry.get(norm_id)
        if not entry:
            self.discover()
            entry = self.registry.get(norm_id)
        if not entry:
            raise ExtensionNotFoundError(f"Extension '{norm_id}' is not installed.", extension_id=norm_id)

        scope = entry.state.scope
        with self.scope_lock(scope, timeout=lock_timeout):
            dest_dir = Path(entry.state.installed_path)
            backup_dir = dest_dir.with_suffix(".backup")
            if not backup_dir.is_dir():
                raise ExtensionError(f"No rollback snapshot available for extension '{norm_id}'.", extension_id=norm_id)

            # Restore from backup
            shutil.rmtree(dest_dir)
            backup_dir.rename(dest_dir)
            self.discover()
            restored = self.registry.get(norm_id)
            if not restored:
                raise ExtensionError("Rollback restoration failed.", extension_id=norm_id)

            # Update persisted state version
            state_dict = self._load_state_dict(scope)
            if norm_id in state_dict:
                state_dict[norm_id].version = restored.manifest.version
                state_dict[norm_id].updated_at = datetime.now(UTC)
                self._save_state_dict(scope, state_dict)
                restored.state = state_dict[norm_id]

            return restored.state

    def uninstall(self, extension_id: str, purge_config: bool = False, lock_timeout: float = 10.0) -> None:
        """Uninstalls an extension, preserving user configuration by default."""
        norm_id = extension_id.strip().lower()
        entry = self.registry.get(norm_id)
        if not entry:
            self.discover()
            entry = self.registry.get(norm_id)
        if not entry:
            raise ExtensionNotFoundError(f"Extension '{norm_id}' is not installed.", extension_id=norm_id)

        scope = entry.state.scope
        with self.scope_lock(scope, timeout=lock_timeout):
            installed_path = Path(entry.state.installed_path)

            # Remove files
            if installed_path.exists():
                shutil.rmtree(installed_path)

            # Update persisted state
            state_dict = self._load_state_dict(scope)
            if not purge_config:
                # Keep record of configuration
                if norm_id in state_dict:
                    state_dict[norm_id].state = ExtensionLifecycleState.NOT_INSTALLED
                    state_dict[norm_id].enabled = False
            else:
                state_dict.pop(norm_id, None)

            self._save_state_dict(scope, state_dict)
            self.registry.unregister(norm_id)

    def diagnose(self) -> list[ExtensionHealthReport]:
        """Runs non-destructive health checks across all installed extensions."""
        self.discover()
        reports: list[ExtensionHealthReport] = []

        for entry in self.registry.list_all():
            checks: list[dict[str, Any]] = []
            is_compat, compat_msg = check_compatibility(entry.manifest)
            checks.append({
                "probe": "compatibility",
                "passed": is_compat,
                "message": compat_msg or "Compatible with host environment",
            })

            path_ok = Path(entry.state.installed_path).is_dir() if entry.state.installed_path else True
            checks.append({
                "probe": "filesystem_intact",
                "passed": path_ok,
                "message": "Filesystem directory exists and is readable" if path_ok else "Installed directory is missing",
            })

            all_passed = all(c["passed"] for c in checks)
            reports.append(
                ExtensionHealthReport(
                    extension_id=entry.manifest.id,
                    version=entry.manifest.version,
                    state=entry.state.state,
                    healthy=all_passed,
                    message="Extension healthy" if all_passed else "Diagnostic issues identified",
                    checks=checks,
                )
            )
        return reports
