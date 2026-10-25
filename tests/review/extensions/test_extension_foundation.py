"""Unit tests for LogicFalcon Extension Platform foundation (manifests, models, compatibility, registry)."""

import pytest

from packages.review.extensions.compatibility import assert_compatible, check_compatibility
from packages.review.extensions.errors import (
    ExtensionAlreadyExistsError,
    ExtensionNotFoundError,
    IncompatibleVersionError,
    ManifestValidationError,
)
from packages.review.extensions.manifest import parse_manifest
from packages.review.extensions.models import (
    ExtensionLifecycleState,
)
from packages.review.extensions.registry import ExtensionRegistry


def test_valid_manifest_parsing_from_dict() -> None:
    data = {
        "schema_version": "1.0.0",
        "id": "org.security-scanner",
        "name": "Security Scanner",
        "version": "1.0.0",
        "description": "Static AST security rules",
        "author": "Security Team <sec@example.com>",
        "compatibility": {
            "logicfalcon": ">=0.1.4",
            "python": ">=3.12",
        },
        "capabilities": [
            {"capability": "fs:read", "description": "Reads source files"},
        ],
        "entry_points": {
            "analyzers": [
                {
                    "name": "sec-scanner",
                    "target": "sec_scanner.analyzer:SecurityAnalyzer",
                    "execution_mode": "in_process",
                }
            ]
        },
        "dependencies": ["cryptography>=42.0.0"],
    }
    manifest = parse_manifest(data)
    assert manifest.id == "org.security-scanner"
    assert manifest.version == "1.0.0"
    assert len(manifest.capabilities) == 1
    assert manifest.has_capability("fs:read")
    assert not manifest.has_capability("net:outbound")
    assert manifest.entry_points["analyzers"][0].name == "sec-scanner"


def test_manifest_parsing_from_yaml_string() -> None:
    yaml_content = """
schema_version: "1.0.0"
id: "com.acme.performance-rules"
name: "Performance Rules"
version: "0.5.2"
description: "Detects hot loops and slow patterns"
capabilities:
  - capability: "fs:read"
entry_points:
  analyzers:
    - name: "perf-rule"
      target: "acme.perf:PerfRule"
"""
    manifest = parse_manifest(yaml_content)
    assert manifest.id == "com.acme.performance-rules"
    assert manifest.version == "0.5.2"
    assert manifest.has_capability("fs:read")


def test_manifest_rejects_invalid_identifiers() -> None:
    # Missing namespace
    with pytest.raises(ManifestValidationError):
        parse_manifest({"schema_version": "1.0.0", "id": "myplugin", "name": "Test", "version": "1.0.0"})

    # Uppercase letters
    with pytest.raises(ManifestValidationError):
        parse_manifest({"schema_version": "1.0.0", "id": "Org.MyPlugin", "name": "Test", "version": "1.0.0"})

    # Spaces and special characters
    with pytest.raises(ManifestValidationError):
        parse_manifest({"schema_version": "1.0.0", "id": "org.my plugin!", "name": "Test", "version": "1.0.0"})


def test_manifest_rejects_invalid_semver() -> None:
    with pytest.raises(ManifestValidationError):
        parse_manifest({
            "schema_version": "1.0.0",
            "id": "org.valid-plugin",
            "name": "Test",
            "version": "1.0",  # Not 3-part semver
        })

    with pytest.raises(ManifestValidationError):
        parse_manifest({
            "schema_version": "1.0.0",
            "id": "org.valid-plugin",
            "name": "Test",
            "version": "v1.0.0",  # Prefix 'v' not allowed in strict semver
        })


def test_manifest_rejects_unsupported_schema_version() -> None:
    with pytest.raises(ManifestValidationError):
        parse_manifest({
            "schema_version": "2.0.0",
            "id": "org.valid-plugin",
            "name": "Test",
            "version": "1.0.0",
        })


def test_manifest_rejects_invalid_capability_format() -> None:
    with pytest.raises(ManifestValidationError):
        parse_manifest({
            "schema_version": "1.0.0",
            "id": "org.valid-plugin",
            "name": "Test",
            "version": "1.0.0",
            "capabilities": [{"capability": "invalid_capability_without_colon"}],
        })


def test_manifest_rejects_path_traversal_in_entry_points() -> None:
    with pytest.raises(ManifestValidationError):
        parse_manifest({
            "schema_version": "1.0.0",
            "id": "org.valid-plugin",
            "name": "Test",
            "version": "1.0.0",
            "entry_points": {
                "analyzers": [
                    {"name": "evil", "target": "../../etc/passwd:Exploit"}
                ]
            },
        })

    with pytest.raises(ManifestValidationError):
        parse_manifest({
            "schema_version": "1.0.0",
            "id": "org.valid-plugin",
            "name": "Test",
            "version": "1.0.0",
            "entry_points": {
                "analyzers": [
                    {"name": "evil", "target": "sub/module:Exploit"}
                ]
            },
        })


def test_compatibility_checker() -> None:
    manifest = parse_manifest({
        "schema_version": "1.0.0",
        "id": "org.compat-test",
        "name": "Compat Test",
        "version": "1.0.0",
        "compatibility": {
            "logicfalcon": ">=0.1.4, <0.2.0",
            "python": ">=3.12",
        },
    })

    # Exact match passes
    is_compat, reason = check_compatibility(
        manifest, current_logicfalcon_version="0.1.4", current_python_version="3.12.1"
    )
    assert is_compat
    assert reason is None

    # LogicFalcon version out of bounds
    is_compat, reason = check_compatibility(
        manifest, current_logicfalcon_version="0.2.0", current_python_version="3.12.1"
    )
    assert not is_compat
    assert "requires LogicFalcon '>=0.1.4, <0.2.0'" in (reason or "")

    # Python version out of bounds
    is_compat, reason = check_compatibility(
        manifest, current_logicfalcon_version="0.1.4", current_python_version="3.11.8"
    )
    assert not is_compat
    assert "requires Python '>=3.12'" in (reason or "")

    # assert_compatible raises
    with pytest.raises(IncompatibleVersionError):
        assert_compatible(manifest, current_logicfalcon_version="0.1.3")


def test_extension_registry_lifecycle() -> None:
    registry = ExtensionRegistry()
    assert len(registry.list_all()) == 0

    manifest = parse_manifest({
        "schema_version": "1.0.0",
        "id": "org.plugin-a",
        "name": "Plugin A",
        "version": "1.0.0",
        "entry_points": {
            "analyzers": [{"name": "analyzer-a", "target": "plugin_a:Rule"}]
        },
    })

    # Register
    entry = registry.register(manifest)
    assert entry.manifest.id == "org.plugin-a"
    assert len(registry.list_all()) == 1
    assert registry.get("org.plugin-a") is not None
    assert registry.get("ORG.PLUGIN-A") is not None  # Case-insensitive

    # Duplicate registration rejected
    with pytest.raises(ExtensionAlreadyExistsError):
        registry.register(manifest)

    # Overwrite permitted when explicitly requested
    entry2 = registry.register(manifest, overwrite=True)
    assert entry2 is not None
    assert len(registry.list_all()) == 1

    # Initially disabled
    assert len(registry.list_enabled()) == 0
    assert len(registry.get_analyzers()) == 0

    # Enable
    entry.state.enabled = True
    entry.state.state = ExtensionLifecycleState.ENABLED
    assert len(registry.list_enabled()) == 1
    analyzers = registry.get_analyzers()
    assert len(analyzers) == 1
    assert analyzers[0][1].name == "analyzer-a"

    # Unregister
    removed = registry.unregister("org.plugin-a")
    assert removed.manifest.id == "org.plugin-a"
    assert len(registry.list_all()) == 0

    # Unregister non-existent raises
    with pytest.raises(ExtensionNotFoundError):
        registry.unregister("org.plugin-a")
