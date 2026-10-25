"""Domain models, schemas, and enums for the LogicFalcon Extension Platform."""

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ExecutionMode(StrEnum):
    """Execution profile and isolation boundary for an extension."""

    IN_PROCESS = "in_process"
    SUBPROCESS_WORKER = "subprocess_worker"
    CONTAINER = "container"


class ExtensionLifecycleState(StrEnum):
    """Operational lifecycle state of an extension."""

    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEGRADED = "degraded"
    UPDATING = "updating"
    UNINSTALLING = "uninstalling"


class ExtensionStorageScope(StrEnum):
    """Filesystem location where the extension is persisted."""

    WORKSPACE = "workspace"
    USER = "user"
    BUILTIN = "builtin"


class CapabilityType(StrEnum):
    """Granular permissions that an extension can request."""

    FS_READ = "fs:read"
    FS_WRITE = "fs:write"
    PROJECT_READ = "project:read"
    PROJECT_ANALYZE = "project:analyze"
    NET_OUTBOUND = "net:outbound"
    NETWORK_HTTP = "network:http"
    ENV_READ = "env:read"
    PROCESS_EXEC = "process:exec"
    FDE_MUTATE = "fde:mutate"


EXTENSION_ID_REGEX = re.compile(r"^[a-z0-9_\-]+(?:\.[a-z0-9_\-]+)+$")
SEMVER_REGEX = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")


class CapabilityRequirement(BaseModel):
    """A declared capability with optional boundary constraints."""

    capability: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capability")
    @classmethod
    def validate_capability_format(cls, v: str) -> str:
        s = v.strip().lower()
        if not s or ":" not in s:
            raise ValueError(f"Capability must follow 'category:action' format, got '{v}'")
        return s


class EntryPointDefinition(BaseModel):
    """Specification of an exported hook or adapter implementation."""

    name: str
    target: str  # Format: "module.submodule:ClassName"
    execution_mode: ExecutionMode = ExecutionMode.IN_PROCESS
    description: str = ""

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        s = v.strip()
        if ":" not in s:
            raise ValueError(f"Entry point target must be formatted as 'module:ClassName', got '{v}'")
        mod, cls_name = s.split(":", 1)
        if not mod or not cls_name:
            raise ValueError(f"Invalid entry point target '{v}'")
        # Prevent traversal in module path
        if ".." in mod or "/" in mod or "\\" in mod:
            raise ValueError(f"Entry point target contains illegal characters or path traversal: '{v}'")
        return s


class ExtensionCompatibility(BaseModel):
    """Compatibility boundaries for LogicFalcon and Python runtime."""

    logicfalcon: str = ">=0.1.4"
    python: str = ">=3.12"


class ExtensionManifest(BaseModel):
    """Strictly validated extension contract and metadata manifest."""

    schema_version: str = "1.0.0"
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = "Apache-2.0"
    compatibility: ExtensionCompatibility = Field(default_factory=ExtensionCompatibility)
    capabilities: list[CapabilityRequirement] = Field(default_factory=list)
    entry_points: dict[str, list[EntryPointDefinition]] = Field(default_factory=dict)
    configuration_schema: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    integrity_hash: str | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        s = v.strip()
        if not EXTENSION_ID_REGEX.match(s):
            raise ValueError(
                f"Extension id must be namespaced lowercase format 'namespace.name' (e.g. 'org.security-rules'), got '{v}'"
            )
        return s

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        s = v.strip()
        if not SEMVER_REGEX.match(s):
            raise ValueError(f"Extension version must follow Semantic Versioning (X.Y.Z), got '{v}'")
        return s

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != "1.0.0":
            raise ValueError(f"Unsupported extension manifest schema version: '{v}'. Supported: '1.0.0'")
        return v

    def has_capability(self, capability_prefix: str) -> bool:
        """Checks if the extension declares a capability starting with the specified prefix."""
        target = capability_prefix.lower()
        for cap in self.capabilities:
            if cap.capability == target or cap.capability.startswith(f"{target}:"):
                return True
        return False


class ExtensionStateRecord(BaseModel):
    """Persistent state record for an installed extension."""

    id: str
    version: str
    state: ExtensionLifecycleState = ExtensionLifecycleState.INSTALLED
    scope: ExtensionStorageScope = ExtensionStorageScope.USER
    installed_path: str
    installed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    enabled: bool = False
    error_message: str | None = None
    user_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtensionHealthReport(BaseModel):
    """Health status and diagnostic probe report for an extension."""

    extension_id: str
    version: str
    state: ExtensionLifecycleState
    healthy: bool
    message: str
    checks: list[dict[str, Any]] = Field(default_factory=list)


class ExtensionAuditEntry(BaseModel):
    """Cryptographically timestamped, append-only audit event for lifecycle operations."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extension_id: str
    event_type: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
