"""Structured error hierarchy for the LogicFalcon Extension Platform."""


class ExtensionError(Exception):
    """Base exception for all extension platform errors."""

    def __init__(self, message: str, extension_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.extension_id = extension_id

    def __str__(self) -> str:
        if self.extension_id:
            return f"[{self.extension_id}] {self.message}"
        return self.message


class ManifestValidationError(ExtensionError):
    """Raised when an extension manifest fails structural, syntactic, or security validation."""

    pass


class IncompatibleVersionError(ExtensionError):
    """Raised when an extension is incompatible with the active LogicFalcon or Python runtime."""

    pass


class ExtensionAlreadyExistsError(ExtensionError):
    """Raised when attempting to install an extension identifier that is already registered."""

    pass


class ExtensionNotFoundError(ExtensionError):
    """Raised when an operation targets an extension identifier that does not exist."""

    pass


class ExtensionDisabledError(ExtensionError):
    """Raised when attempting to execute an extension that is installed but currently disabled."""

    pass


class PermissionDeniedError(ExtensionError):
    """Raised when an extension attempts an undeclared, unauthorized, or unapproved operation."""

    pass


class CapabilityDeniedError(PermissionDeniedError):
    """Raised when an extension attempts an operation for which it has not declared the required capability."""

    def __init__(self, message: str, extension_id: str | None = None, capability: str | None = None) -> None:
        super().__init__(message, extension_id=extension_id)
        self.capability = capability


class ApprovalRequiredError(PermissionDeniedError):
    """Raised when an extension attempts a mutating operation requiring explicit parameter-bound approval."""

    pass


class SecurityViolationError(ExtensionError):
    """Raised when an extension violates security boundaries (e.g., path traversal, SSRF, tampering)."""

    pass


class ExtensionSecurityError(SecurityViolationError):
    """Specific security violation such as path traversal, SSRF attempt, or access to protected files."""

    pass


class ExtensionExecutionError(ExtensionError):
    """Raised when an extension runtime raises an unhandled exception or returns malformed results."""

    pass


class WorkerCrashError(ExtensionError):
    """Raised when an out-of-process extension worker unexpectedly terminates or crashes."""

    pass


class LockContentionError(ExtensionError):
    """Raised when an extension operation cannot acquire an inter-process scope lock within timeout."""

    def __init__(
        self,
        message: str,
        extension_id: str | None = None,
        scope: str | None = None,
        lock_path: str | None = None,
    ) -> None:
        super().__init__(message, extension_id=extension_id)
        self.scope = scope
        self.lock_path = lock_path


class CatalogError(ExtensionError):
    """Raised when interacting with an extension catalog fails or returns malformed metadata."""

    pass
