"""Version compatibility and environment evaluation for LogicFalcon extensions."""

import sys

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

try:
    import logicfalcon
    CURRENT_LOGICFALCON_VERSION = getattr(logicfalcon, "__version__", "0.1.5")
except Exception:
    CURRENT_LOGICFALCON_VERSION = "0.1.5"

from packages.review.extensions.errors import IncompatibleVersionError
from packages.review.extensions.models import ExtensionManifest


def get_current_python_version() -> str:
    """Returns the current runtime Python version formatted as X.Y.Z."""
    v = sys.version_info
    return f"{v.major}.{v.minor}.{v.micro}"


def check_compatibility(
    manifest: ExtensionManifest,
    current_logicfalcon_version: str | None = None,
    current_python_version: str | None = None,
) -> tuple[bool, str | None]:
    """Evaluates whether an extension is compatible with the host runtime.

    Returns:
        (is_compatible, reason_if_incompatible)
    """
    lf_ver_str = current_logicfalcon_version or CURRENT_LOGICFALCON_VERSION
    py_ver_str = current_python_version or get_current_python_version()

    # 1. Evaluate LogicFalcon version constraint
    lf_spec = manifest.compatibility.logicfalcon
    try:
        spec_set = SpecifierSet(lf_spec)
        parsed_lf_ver = Version(lf_ver_str)
        if parsed_lf_ver not in spec_set:
            return (
                False,
                f"Extension '{manifest.id}' requires LogicFalcon '{lf_spec}', but host is running '{lf_ver_str}'.",
            )
    except (InvalidSpecifier, InvalidVersion) as e:
        return (
            False,
            f"Invalid LogicFalcon version constraint or version specifier '{lf_spec}': {e}",
        )

    # 2. Evaluate Python runtime version constraint
    py_spec = manifest.compatibility.python
    try:
        spec_set = SpecifierSet(py_spec)
        parsed_py_ver = Version(py_ver_str)
        if parsed_py_ver not in spec_set:
            return (
                False,
                f"Extension '{manifest.id}' requires Python '{py_spec}', but host runtime is '{py_ver_str}'.",
            )
    except (InvalidSpecifier, InvalidVersion) as e:
        return (
            False,
            f"Invalid Python version constraint or version specifier '{py_spec}': {e}",
        )

    return True, None


def assert_compatible(
    manifest: ExtensionManifest,
    current_logicfalcon_version: str | None = None,
    current_python_version: str | None = None,
) -> None:
    """Asserts compatibility, raising IncompatibleVersionError if constraints are violated."""
    is_compat, reason = check_compatibility(
        manifest=manifest,
        current_logicfalcon_version=current_logicfalcon_version,
        current_python_version=current_python_version,
    )
    if not is_compat:
        raise IncompatibleVersionError(reason or "Incompatible extension version.", extension_id=manifest.id)
