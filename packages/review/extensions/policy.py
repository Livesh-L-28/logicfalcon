"""Security boundaries, capability enforcement, and sandboxing for LogicFalcon extensions."""

import ipaddress
import re
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from packages.review.adapters.ast_security import redact_secrets_in_text
from packages.review.extensions.errors import (
    ApprovalRequiredError,
    CapabilityDeniedError,
    ExtensionSecurityError,
)
from packages.review.extensions.models import (
    CapabilityType,
    ExtensionAuditEntry,
    ExtensionManifest,
)

# Protected paths that must never be accessed under any circumstances
_FORBIDDEN_EXACT_PATHS = {
    Path("/Users/livesh/AEGIS AI/render_schema.json").resolve(),
}
_FORBIDDEN_PREFIX_PATHS = [
    Path("/Users/livesh/AEGIS-Framework").resolve(),
]

# Private and cloud metadata IP ranges prohibited for SSRF defense
_PROHIBITED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local & Cloud IMDS (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
]


def validate_contained_path(
    path: Path | str,
    allowed_roots: list[Path | str],
    allow_symlinks: bool = False,
) -> Path:
    """Validates that a path is strictly contained within at least one allowed root directory.

    Rejects path traversal, symlink escapes, and non-negotiable protected paths.
    """
    raw_path = Path(path)
    try:
        resolved_path = raw_path.resolve()
    except Exception as e:
        raise ExtensionSecurityError(f"Failed to resolve path '{path}': {e}") from e

    # 1. Non-negotiable protected path checks
    if resolved_path in _FORBIDDEN_EXACT_PATHS:
        raise ExtensionSecurityError(
            f"Security Violation: Access to protected path '{resolved_path}' is strictly prohibited."
        )

    for forbidden_prefix in _FORBIDDEN_PREFIX_PATHS:
        if resolved_path == forbidden_prefix or forbidden_prefix in resolved_path.parents:
            raise ExtensionSecurityError(
                f"Security Violation: Access to protected prefix '{forbidden_prefix}' is strictly prohibited."
            )

    # 2. Allowed roots containment check
    resolved_roots = [Path(r).resolve() for r in allowed_roots]
    is_contained = False

    for root in resolved_roots:
        if resolved_path == root or root in resolved_path.parents:
            is_contained = True
            break

    if not is_contained:
        raise ExtensionSecurityError(
            f"Path containment violation: '{resolved_path}' is not within approved roots: {resolved_roots}"
        )

    # 3. Symlink check if symlinks are disallowed
    if not allow_symlinks and raw_path.is_symlink():
        raise ExtensionSecurityError(f"Symlinks are disallowed for secure path access: '{raw_path}'")

    return resolved_path


def validate_safe_url(url: str, allowed_schemes: tuple[str, ...] = ("http", "https")) -> str:
    """Validates that an outbound URL does not target loopback, link-local, private, or metadata IPs."""
    if any(c in url for c in ("\r", "\n", "\0")):
        raise ExtensionSecurityError("URL contains illegal control characters.")

    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme.lower() not in allowed_schemes:
        raise ExtensionSecurityError(f"Prohibited URL scheme '{parsed.scheme}'. Allowed: {allowed_schemes}")

    hostname = parsed.hostname
    if not hostname:
        raise ExtensionSecurityError("URL is missing a valid hostname.")

    # Check for direct IP literals
    try:
        ip = ipaddress.ip_address(hostname)
        for prohibited_net in _PROHIBITED_IP_NETWORKS:
            if ip in prohibited_net:
                raise ExtensionSecurityError(
                    f"SSRF Protection: Access to private/reserved IP '{ip}' is strictly blocked."
                )
        return url
    except ValueError:
        # Not a direct IP literal, check DNS resolution
        pass

    # Resolve hostname to check target IPs
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            resolved_ip_str = sockaddr[0]
            resolved_ip = ipaddress.ip_address(resolved_ip_str)
            for prohibited_net in _PROHIBITED_IP_NETWORKS:
                if resolved_ip in prohibited_net:
                    raise ExtensionSecurityError(
                        f"SSRF Protection: Hostname '{hostname}' resolves to private/reserved IP '{resolved_ip}', access blocked."
                    )
    except socket.gaierror:
        # Re-raise socket.gaierror as resolution/network failure rather than security violation
        raise

    return url


_ADDITIONAL_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(?:bearer\s+)([a-zA-Z0-9_\-\.=/+]{16,})"),
    re.compile(r"\b(?:sk-ant-[a-zA-Z0-9_\-]{10,}|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16})\b"),
]


class CapabilityGateway:
    """Enforces capability declarations, parameter-bound approval, and audit trails for extensions."""

    def __init__(self, fde_policy_gateway: Any | None = None) -> None:
        self.fde_policy_gateway = fde_policy_gateway
        self.audit_log: list[ExtensionAuditEntry] = []

    def check_capability(
        self,
        manifest: ExtensionManifest,
        required_capability: CapabilityType | str,
        target: str = "",
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Verifies if an extension has declared the requested capability."""
        cap_val = required_capability.value if isinstance(required_capability, CapabilityType) else str(required_capability)
        declared = {c.capability for c in manifest.capabilities}

        allowed = cap_val in declared
        reason = "Capability declared in manifest" if allowed else f"Capability '{cap_val}' not declared in manifest"

        self.audit_log.append(
            ExtensionAuditEntry(
                timestamp=datetime.now(UTC),
                extension_id=manifest.id,
                event_type="capability_check",
                status="allowed" if allowed else "denied",
                details={
                    "capability": cap_val,
                    "target": target,
                    "allowed": allowed,
                    "reason": reason,
                    **(details or {}),
                },
            )
        )

        if not allowed:
            raise CapabilityDeniedError(
                f"Extension '{manifest.id}' denied capability '{cap_val}'. "
                f"Declared capabilities: {sorted(declared)}",
                extension_id=manifest.id,
                capability=cap_val,
            )
        return True

    def authorize_mutation(
        self,
        manifest: ExtensionManifest,
        mission_id: str,
        step_id: str,
        adapter_id: str,
        operation: str,
        target: str,
        params: dict[str, Any],
        approval_token: str | None = None,
    ) -> bool:
        """Enforces both manifest capability and FDE PolicyGateway parameter-bound approval for mutating operations."""
        # 1. First enforce declared capability
        self.check_capability(manifest, CapabilityType.FDE_MUTATE, target=target)

        # 2. Check FDE PolicyGateway if configured
        if self.fde_policy_gateway is not None:
            expected_token = self.fde_policy_gateway.compute_approval_token(
                mission_id=mission_id,
                step_id=step_id,
                adapter_id=adapter_id,
                operation=operation,
                target=target,
                params=params,
            )
            if not approval_token or approval_token != expected_token:
                reason = "Missing or mismatched cryptographic approval token"
                self.audit_log.append(
                    ExtensionAuditEntry(
                        timestamp=datetime.now(UTC),
                        extension_id=manifest.id,
                        event_type="mutation_authorization",
                        status="denied",
                        details={
                            "capability": CapabilityType.FDE_MUTATE.value,
                            "target": target,
                            "reason": reason,
                        },
                    )
                )
                raise ApprovalRequiredError(
                    f"Mutating operation '{operation}' on '{target}' requires valid approval token.",
                    extension_id=manifest.id,
                )

            # Check if token is authorized in gateway
            if not self.fde_policy_gateway.is_approved(mission_id, step_id, adapter_id, operation, target, params):
                reason = "Approval token was not granted or has been revoked"
                self.audit_log.append(
                    ExtensionAuditEntry(
                        timestamp=datetime.now(UTC),
                        extension_id=manifest.id,
                        event_type="mutation_authorization",
                        status="denied",
                        details={
                            "capability": CapabilityType.FDE_MUTATE.value,
                            "target": target,
                            "reason": reason,
                        },
                    )
                )
                raise ApprovalRequiredError(reason, extension_id=manifest.id)

            self.audit_log.append(
                ExtensionAuditEntry(
                    timestamp=datetime.now(UTC),
                    extension_id=manifest.id,
                    event_type="mutation_authorization",
                    status="allowed",
                    details={
                        "capability": CapabilityType.FDE_MUTATE.value,
                        "target": target,
                        "operation": operation,
                        "adapter_id": adapter_id,
                    },
                )
            )

        return True

    def sanitize_message(self, text: str) -> str:
        """Redacts secrets, API keys, and sensitive tokens from extension output or error messages."""
        res = redact_secrets_in_text(text)
        for pattern in _ADDITIONAL_SECRET_PATTERNS:
            res = pattern.sub("[REDACTED_SECRET]", res)
        return res
