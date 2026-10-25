"""Comprehensive concurrency and inter-process locking tests for LogicFalcon Extension Platform (SEC-002)."""

import os
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from packages.review.extensions.errors import LockContentionError
from packages.review.extensions.manager import ExtensionManager
from packages.review.extensions.models import ExtensionLifecycleState, ExtensionStorageScope
from packages.review.extensions.registry import ExtensionRegistry


@pytest.fixture
def isolated_dirs(tmp_path: Path) -> tuple[Path, Path]:
    user_dir = tmp_path / "user_exts"
    workspace_dir = tmp_path / "workspace_exts"
    user_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return user_dir, workspace_dir


@pytest.fixture
def sample_extension_source(tmp_path: Path) -> Path:
    ext_dir = tmp_path / "sample_ext"
    ext_dir.mkdir(parents=True, exist_ok=True)
    manifest_yaml = """
id: "org.test.concurrent-tool"
name: "Concurrent Test Tool"
version: "1.0.0"
min_logicfalcon: ">=0.1.4"
min_python: ">=3.12"
entrypoint: "tool.py:entry"
capabilities: []
"""
    (ext_dir / "extension.yaml").write_text(manifest_yaml.strip(), encoding="utf-8")
    (ext_dir / "tool.py").write_text("def entry(): pass\n", encoding="utf-8")
    return ext_dir


def test_scope_lock_acquisition_permissions_and_release(isolated_dirs: tuple[Path, Path]) -> None:
    user_dir, workspace_dir = isolated_dirs
    manager = ExtensionManager(user_dir=user_dir, workspace_dir=workspace_dir, registry=ExtensionRegistry())

    scope = ExtensionStorageScope.USER
    with manager.scope_lock(scope, timeout=2.0):
        lock_file = user_dir / ".lock"
        assert lock_file.is_file()
        # Verify 0o600 permissions
        file_mode = stat.S_IMODE(os.stat(lock_file).st_mode)
        assert file_mode == 0o600


def test_scope_lock_reentrancy_in_same_thread(isolated_dirs: tuple[Path, Path]) -> None:
    user_dir, workspace_dir = isolated_dirs
    manager = ExtensionManager(user_dir=user_dir, workspace_dir=workspace_dir, registry=ExtensionRegistry())

    scope = ExtensionStorageScope.WORKSPACE
    # Nested locks in the same thread should not block or deadlock
    with (
        manager.scope_lock(scope, timeout=1.0),
        manager.scope_lock(scope, timeout=1.0),
        manager.scope_lock(scope, timeout=1.0),
    ):
        lock_file = workspace_dir / ".lock"
        assert lock_file.is_file()


def test_scope_lock_contention_between_threads(isolated_dirs: tuple[Path, Path]) -> None:
    user_dir, workspace_dir = isolated_dirs
    manager = ExtensionManager(user_dir=user_dir, workspace_dir=workspace_dir, registry=ExtensionRegistry())
    scope = ExtensionStorageScope.USER

    held_event = threading.Event()
    release_event = threading.Event()

    def background_holder() -> None:
        with manager.scope_lock(scope, timeout=2.0):
            held_event.set()
            release_event.wait(timeout=2.0)

    t = threading.Thread(target=background_holder, daemon=True)
    t.start()
    assert held_event.wait(timeout=2.0)

    try:
        # Contention should raise LockContentionError after timeout
        with pytest.raises(LockContentionError) as exc_info, manager.scope_lock(scope, timeout=0.1):
            pass
        assert "Timed out" in str(exc_info.value)
        assert exc_info.value.scope == scope.value
    finally:
        release_event.set()
        t.join(timeout=1.0)


def test_scope_lock_interprocess_contention(
    isolated_dirs: tuple[Path, Path], sample_extension_source: Path
) -> None:
    user_dir, workspace_dir = isolated_dirs
    manager = ExtensionManager(user_dir=user_dir, workspace_dir=workspace_dir, registry=ExtensionRegistry())
    scope = ExtensionStorageScope.USER
    lock_file = user_dir / ".lock"
    user_dir.mkdir(parents=True, exist_ok=True)

    # Spawn an external Python process that holds flock
    script = f"""
import fcntl, os, time
fd = os.open({str(lock_file)!r}, os.O_RDWR | os.O_CREAT, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX)
print("ACQUIRED", flush=True)
time.sleep(2.0)
"""
    proc = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True)
    try:
        # Wait until subprocess acquires lock
        line = proc.stdout.readline().strip()
        assert line == "ACQUIRED"

        # Attempt to install extension while external process holds lock
        with pytest.raises(LockContentionError) as exc_info:
            manager.install(sample_extension_source, scope=scope, lock_timeout=0.1)

        assert "Timed out" in str(exc_info.value)
        assert exc_info.value.scope == scope.value
    finally:
        proc.kill()
        proc.wait()


def test_scope_lock_subprocess_crash_cleanup(
    isolated_dirs: tuple[Path, Path], sample_extension_source: Path
) -> None:
    user_dir, workspace_dir = isolated_dirs
    manager = ExtensionManager(user_dir=user_dir, workspace_dir=workspace_dir, registry=ExtensionRegistry())
    scope = ExtensionStorageScope.WORKSPACE
    lock_file = workspace_dir / ".lock"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Spawn a subprocess that acquires flock then abruptly terminates with SIGKILL / exit code
    script = f"""
import fcntl, os, sys
fd = os.open({str(lock_file)!r}, os.O_RDWR | os.O_CREAT, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX)
print("LOCKED", flush=True)
sys.stdout.flush()
# Abrupt crash without cleanup
os._exit(99)
"""
    proc = subprocess.run([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True)
    assert proc.returncode == 99

    # The OS kernel automatically frees flock upon process termination
    # Manager must be able to acquire lock immediately and succeed
    plan = manager.install(sample_extension_source, scope=scope, lock_timeout=1.0)
    assert plan.extension_id == "org.test.concurrent-tool"

    record = manager.enable(plan.extension_id, lock_timeout=1.0)
    assert record.enabled is True
    assert record.state == ExtensionLifecycleState.ENABLED


def test_concurrent_mutations_preserve_state_integrity(
    isolated_dirs: tuple[Path, Path], sample_extension_source: Path
) -> None:
    user_dir, workspace_dir = isolated_dirs
    manager = ExtensionManager(user_dir=user_dir, workspace_dir=workspace_dir, registry=ExtensionRegistry())
    scope = ExtensionStorageScope.USER

    # Install extension first
    manager.install(sample_extension_source, scope=scope)

    errors: list[Exception] = []

    def toggle_state(worker_id: int) -> None:
        for _ in range(5):
            try:
                if worker_id % 2 == 0:
                    manager.enable("org.test.concurrent-tool", lock_timeout=3.0)
                else:
                    manager.disable("org.test.concurrent-tool", lock_timeout=3.0)
            except Exception as e:
                errors.append(e)
            time.sleep(0.01)

    threads = [threading.Thread(target=toggle_state, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    # No unhandled exceptions or state corruption
    assert len(errors) == 0

    # Verify state.json is valid and parseable
    state_file = user_dir / "state.json"
    assert state_file.is_file()
    state_dict = manager._load_state_dict(scope)
    assert "org.test.concurrent-tool" in state_dict
    assert state_dict["org.test.concurrent-tool"].version == "1.0.0"
