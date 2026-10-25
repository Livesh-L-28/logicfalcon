"""Comprehensive security and permission tests for LogicFalcon Extensions (Phase 3)."""

from pathlib import Path

import pytest

from packages.review.extensions.errors import (
    ApprovalRequiredError,
    CapabilityDeniedError,
    ExtensionSecurityError,
)
from packages.review.extensions.models import (
    CapabilityRequirement,
    CapabilityType,
    ExtensionManifest,
)
from packages.review.extensions.policy import (
    CapabilityGateway,
    validate_contained_path,
    validate_safe_url,
)
from packages.review.fde.adapters.registry import AdapterRegistry
from packages.review.fde.orchestration.policy_gateway import PolicyGateway


def make_manifest(caps: list[str]) -> ExtensionManifest:
    return ExtensionManifest(
        schema_version="1.0.0",
        id="com.acme.security-scanner",
        name="Security Scanner",
        version="1.0.0",
        author="ACME",
        capabilities=[CapabilityRequirement(capability=c) for c in caps],
    )


def test_path_containment_and_traversal_defense(tmp_path: Path) -> None:
    root = tmp_path / "allowed_root"
    root.mkdir()
    safe_file = root / "safe.py"
    safe_file.write_text("print('safe')", encoding="utf-8")

    # Safe access
    res = validate_contained_path(safe_file, allowed_roots=[root])
    assert res == safe_file.resolve()

    # Traversal escape
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("print('outside')", encoding="utf-8")
    with pytest.raises(ExtensionSecurityError, match="Path containment violation"):
        validate_contained_path(outside_file, allowed_roots=[root])

    # Traversal relative path escape
    traversal_path = root / ".." / "outside.py"
    with pytest.raises(ExtensionSecurityError, match="Path containment violation"):
        validate_contained_path(traversal_path, allowed_roots=[root])


def test_protected_paths_strictly_blocked(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    # Protected render_schema.json
    protected_schema = Path("/Users/livesh/AEGIS AI/render_schema.json")
    with pytest.raises(ExtensionSecurityError, match="Security Violation"):
        validate_contained_path(protected_schema, allowed_roots=[Path("/Users/livesh/AEGIS AI")])

    # Protected AEGIS-Framework prefix
    protected_framework = Path("/Users/livesh/AEGIS-Framework/any_file.py")
    with pytest.raises(ExtensionSecurityError, match="Security Violation"):
        validate_contained_path(protected_framework, allowed_roots=[Path("/Users/livesh")])


def test_ssrf_prohibits_private_and_metadata_ips() -> None:
    # Localhost / loopback
    with pytest.raises(ExtensionSecurityError, match="SSRF Protection"):
        validate_safe_url("http://127.0.0.1:8080/admin")

    # Cloud IMDS metadata IP
    with pytest.raises(ExtensionSecurityError, match="SSRF Protection"):
        validate_safe_url("http://169.254.169.254/latest/meta-data/")

    # RFC 1918 Private ranges
    with pytest.raises(ExtensionSecurityError, match="SSRF Protection"):
        validate_safe_url("http://10.0.0.5/api")

    with pytest.raises(ExtensionSecurityError, match="SSRF Protection"):
        validate_safe_url("http://192.168.1.100/status")

    # Prohibited scheme
    with pytest.raises(ExtensionSecurityError, match="Prohibited URL scheme"):
        validate_safe_url("file:///etc/passwd")


def test_capability_enforcement() -> None:
    manifest = make_manifest(["project:read", "project:analyze"])
    gateway = CapabilityGateway()

    # Allowed declared capabilities
    assert gateway.check_capability(manifest, "project:read") is True
    assert gateway.check_capability(manifest, CapabilityType.PROJECT_ANALYZE) is True

    # Denied undeclared capability
    with pytest.raises(CapabilityDeniedError, match="denied capability 'network:http'"):
        gateway.check_capability(manifest, "network:http")

    assert len(gateway.audit_log) == 3
    assert gateway.audit_log[0].status == "allowed"
    assert gateway.audit_log[1].status == "allowed"
    assert gateway.audit_log[2].status == "denied"


def test_fde_mutation_requires_cryptographic_approval_token() -> None:
    manifest = make_manifest(["fde:mutate"])
    fde_registry = AdapterRegistry()
    fde_gateway = PolicyGateway(registry=fde_registry)
    cap_gateway = CapabilityGateway(fde_policy_gateway=fde_gateway)

    mission_id = "m-test"
    step_id = "s-001"
    adapter_id = "local_process"
    operation = "run_command"
    target = "workspace"
    params = {"cmd": "echo test"}

    # 1. Mutating without approval token fails
    with pytest.raises(ApprovalRequiredError, match="requires valid approval token"):
        cap_gateway.authorize_mutation(
            manifest=manifest,
            mission_id=mission_id,
            step_id=step_id,
            adapter_id=adapter_id,
            operation=operation,
            target=target,
            params=params,
            approval_token=None,
        )

    # 2. Mutating with forged or mismatched token fails
    with pytest.raises(ApprovalRequiredError, match="requires valid approval token"):
        cap_gateway.authorize_mutation(
            manifest=manifest,
            mission_id=mission_id,
            step_id=step_id,
            adapter_id=adapter_id,
            operation=operation,
            target=target,
            params=params,
            approval_token="forged-token-abc",
        )

    # 3. Compute real token but don't grant it yet in PolicyGateway
    valid_token = fde_gateway.compute_approval_token(
        mission_id, step_id, adapter_id, operation, target, params
    )
    with pytest.raises(ApprovalRequiredError, match="not granted or has been revoked"):
        cap_gateway.authorize_mutation(
            manifest=manifest,
            mission_id=mission_id,
            step_id=step_id,
            adapter_id=adapter_id,
            operation=operation,
            target=target,
            params=params,
            approval_token=valid_token,
        )

    # 4. Grant approval in PolicyGateway and verify authorization succeeds
    granted_token = fde_gateway.grant_approval(
        mission_id, step_id, adapter_id, operation, target, params
    )
    assert granted_token == valid_token
    assert cap_gateway.authorize_mutation(
        manifest=manifest,
        mission_id=mission_id,
        step_id=step_id,
        adapter_id=adapter_id,
        operation=operation,
        target=target,
        params=params,
        approval_token=granted_token,
    ) is True


def test_secret_redaction_in_output() -> None:
    gateway = CapabilityGateway()
    sensitive_text = "Encountered error connecting with Bearer sk-ant-api03-abcdef123456789 to host"
    sanitized = gateway.sanitize_message(sensitive_text)
    assert "sk-ant-api03-abcdef123456789" not in sanitized
    assert "[REDACTED" in sanitized or "***" in sanitized
