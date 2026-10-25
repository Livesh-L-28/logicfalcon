"""Subprocess worker entry point for isolated LogicFalcon extension execution."""

import importlib
import json
import sys
from pathlib import Path

from packages.review.extensions.base import (
    ExtensionExecutionContext,
    ExtensionExecutionResult,
)


def main() -> None:
    """Reads execution request from stdin, executes extension, and writes result to stdout."""
    try:
        raw_in = sys.stdin.read()
        if not raw_in.strip():
            sys.stderr.write("Worker received empty input payload.\n")
            sys.exit(2)

        data = json.loads(raw_in)
        module_path = data.get("module_path")
        module_name = data.get("module_name")
        class_name = data.get("class_name")
        target_files = [Path(p) for p in data.get("target_files", [])]
        workspace_root = Path(data.get("workspace_root", "."))
        config = data.get("config", {})
        extension_id = data.get("extension_id", "unknown")

        if module_path and module_path not in sys.path:
            sys.path.insert(0, module_path)

        # Dynamic import
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        ext_instance = cls()

        ctx = ExtensionExecutionContext(
            extension_id=extension_id,
            workspace_root=workspace_root,
            config=config,
        )

        ext_instance.initialize(ctx)
        result: ExtensionExecutionResult = ext_instance.execute(target_files, ctx)
        ext_instance.teardown()

        # Output JSON response
        out_data = {
            "success": result.success,
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "title": f.title,
                    "message": f.message,
                    "file_path": f.file_path,
                    "start_line": f.start_line,
                    "end_line": f.end_line,
                    "severity": f.severity,
                    "suggestion": f.suggestion,
                    "data": f.data,
                }
                for f in result.findings
            ],
            "metrics": result.metrics,
            "error_message": result.error_message,
        }
        sys.stdout.write(json.dumps(out_data) + "\n")
        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"Worker runtime error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
