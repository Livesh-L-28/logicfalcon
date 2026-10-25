"""Parser and validator for LogicFalcon extension manifests."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from packages.review.extensions.errors import ManifestValidationError
from packages.review.extensions.models import ExtensionManifest


def parse_manifest(source: str | dict[str, Any] | Path) -> ExtensionManifest:
    """Parses and strictly validates an extension manifest from raw string, dict, or file path.

    Guarantees:
    - Never imports or executes extension code.
    - Never makes network requests.
    - Never writes or mutates files.
    - Rejects path traversal and malformed inputs.
    """
    raw_data: dict[str, Any]

    if isinstance(source, dict):
        raw_data = source
    elif isinstance(source, Path) or (isinstance(source, str) and (source.endswith(".json") or source.endswith(".yaml") or source.endswith(".yml")) and "\n" not in source):
        path = Path(source)
        if not path.is_file():
            raise ManifestValidationError(f"Manifest file does not exist: {path}")
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            raise ManifestValidationError(f"Failed to read manifest file '{path}': {e}") from e
        raw_data = _parse_content_string(content, path.name)
    elif isinstance(source, str):
        raw_data = _parse_content_string(source, "raw_string")
    else:
        raise ManifestValidationError(f"Unsupported manifest source type: {type(source)}")

    try:
        manifest = ExtensionManifest.model_validate(raw_data)
    except ValidationError as e:
        error_details = []
        for err in e.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Validation error")
            error_details.append(f"Field '{loc}': {msg}")
        raise ManifestValidationError(
            "Extension manifest schema validation failed:\n  " + "\n  ".join(error_details)
        ) from e
    except Exception as e:
        raise ManifestValidationError(f"Unexpected error validating manifest: {e}") from e

    return manifest


def _parse_content_string(content: str, source_name: str) -> dict[str, Any]:
    """Helper to parse JSON or YAML string safely."""
    content_clean = content.strip()
    if not content_clean:
        raise ManifestValidationError(f"Manifest source '{source_name}' is empty.")

    # Try JSON first
    if content_clean.startswith("{"):
        try:
            data = json.loads(content_clean)
            if not isinstance(data, dict):
                raise ManifestValidationError("JSON manifest must be an object at root level.")
            return data
        except json.JSONDecodeError as e:
            raise ManifestValidationError(f"Malformed JSON in manifest '{source_name}': {e}") from e

    # Fallback to YAML
    try:
        import yaml

        data = yaml.safe_load(content_clean)
        if not isinstance(data, dict):
            raise ManifestValidationError("YAML manifest must define a dictionary at root level.")
        return data
    except Exception as e:
        raise ManifestValidationError(f"Failed to parse manifest YAML in '{source_name}': {e}") from e
