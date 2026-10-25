"""In-memory extension registry for runtime lookup and integration."""

from dataclasses import dataclass
from typing import Any

from packages.review.extensions.errors import ExtensionAlreadyExistsError, ExtensionNotFoundError
from packages.review.extensions.models import (
    EntryPointDefinition,
    ExtensionLifecycleState,
    ExtensionManifest,
    ExtensionStateRecord,
)


@dataclass
class RegisteredExtension:
    """Runtime representation of an extension registered with the platform."""

    manifest: ExtensionManifest
    state: ExtensionStateRecord
    instance: Any = None
    loaded: bool = False
    error: str | None = None


class ExtensionRegistry:
    """In-memory registry managing registered extension metadata and hook lookups."""

    def __init__(self) -> None:
        self._extensions: dict[str, RegisteredExtension] = {}

    def register(
        self,
        manifest: ExtensionManifest,
        state: ExtensionStateRecord | None = None,
        overwrite: bool = False,
    ) -> RegisteredExtension:
        """Registers an extension manifest and its state record into the registry."""
        norm_id = manifest.id.lower()
        if norm_id in self._extensions and not overwrite:
            raise ExtensionAlreadyExistsError(
                f"Extension '{norm_id}' is already registered.", extension_id=norm_id
            )

        if state is None:
            if norm_id in self._extensions:
                state = self._extensions[norm_id].state
                state.version = manifest.version
            else:
                state = ExtensionStateRecord(
                    id=norm_id,
                    version=manifest.version,
                    state=ExtensionLifecycleState.INSTALLED,
                    installed_path="",
                    enabled=False,
                )

        entry = RegisteredExtension(manifest=manifest, state=state)
        self._extensions[norm_id] = entry
        return entry

    def unregister(self, extension_id: str) -> RegisteredExtension:
        """Unregisters an extension from the registry."""
        norm_id = extension_id.strip().lower()
        if norm_id not in self._extensions:
            raise ExtensionNotFoundError(f"Extension '{norm_id}' is not registered.", extension_id=norm_id)
        return self._extensions.pop(norm_id)

    def get(self, extension_id: str) -> RegisteredExtension | None:
        """Retrieves a registered extension by ID."""
        return self._extensions.get(extension_id.strip().lower())

    def list_all(self) -> list[RegisteredExtension]:
        """Returns all registered extensions sorted deterministically by ID."""
        return sorted(self._extensions.values(), key=lambda x: x.manifest.id)

    def list_enabled(self) -> list[RegisteredExtension]:
        """Returns all enabled and active extensions."""
        return [
            ext for ext in self.list_all()
            if ext.state.enabled and ext.state.state == ExtensionLifecycleState.ENABLED
        ]

    def get_analyzers(self) -> list[tuple[RegisteredExtension, EntryPointDefinition]]:
        """Discovers all static analyzer entry points provided by enabled extensions."""
        results: list[tuple[RegisteredExtension, EntryPointDefinition]] = []
        for ext in self.list_enabled():
            analyzers = ext.manifest.entry_points.get("analyzers", [])
            for ep in analyzers:
                results.append((ext, ep))
        return results

    def get_fde_adapters(self) -> list[tuple[RegisteredExtension, EntryPointDefinition]]:
        """Discovers all FDE adapter entry points provided by enabled extensions."""
        results: list[tuple[RegisteredExtension, EntryPointDefinition]] = []
        for ext in self.list_enabled():
            adapters = ext.manifest.entry_points.get("fde_adapters", [])
            for ep in adapters:
                results.append((ext, ep))
        return results

    def clear(self) -> None:
        """Clears all in-memory registrations."""
        self._extensions.clear()


# Global in-memory registry instance for application runtime
global_extension_registry = ExtensionRegistry()
