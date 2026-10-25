"""Execution runner supporting in-process and isolated subprocess worker execution modes."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from packages.review.extensions.base import (
    BaseExtension,
    ExtensionExecutionContext,
    ExtensionExecutionResult,
    ExtensionFinding,
)
from packages.review.extensions.errors import (
    ExtensionExecutionError,
    WorkerCrashError,
)
from packages.review.extensions.models import (
    EntryPointDefinition,
    ExecutionMode,
    ExtensionManifest,
)
from packages.review.extensions.policy import CapabilityGateway

MAX_OUTPUT_BYTES = 5 * 1024 * 1024  # 5 MB maximum payload cap


class ExtensionRunner:
    """Executes extensions either in-process or within an isolated worker subprocess."""

    def __init__(self, capability_gateway: CapabilityGateway | None = None) -> None:
        self.gateway = capability_gateway or CapabilityGateway()

    def execute(
        self,
        manifest: ExtensionManifest,
        installed_path: Path | str,
        target_files: list[Path],
        context: ExtensionExecutionContext,
        entry_point_name: str = "default",
        timeout_seconds: float = 30.0,
        force_mode: ExecutionMode | None = None,
    ) -> ExtensionExecutionResult:
        """Executes the specified extension entry point on target files."""
        inst_dir = Path(installed_path)

        # Locate entry point
        ep = self._resolve_entry_point(manifest, entry_point_name)
        mode = force_mode or ep.execution_mode

        if mode == ExecutionMode.IN_PROCESS:
            return self._execute_in_process(manifest, inst_dir, ep, target_files, context)
        else:
            return self._execute_subprocess(manifest, inst_dir, ep, target_files, context, timeout_seconds)

    def _resolve_entry_point(self, manifest: ExtensionManifest, name: str) -> EntryPointDefinition:
        for ep_list in manifest.entry_points.values():
            for ep in ep_list:
                if ep.name == name or name == "default":
                    return ep
        # Fallback to first available entry point
        for ep_list in manifest.entry_points.values():
            if ep_list:
                return ep_list[0]
        raise ExtensionExecutionError(f"No entry point matching '{name}' declared in manifest '{manifest.id}'.", extension_id=manifest.id)

    def _execute_in_process(
        self,
        manifest: ExtensionManifest,
        installed_dir: Path,
        ep: EntryPointDefinition,
        target_files: list[Path],
        context: ExtensionExecutionContext,
    ) -> ExtensionExecutionResult:
        """Loads and executes the extension directly in-process."""
        mod_rel, cls_name = ep.target.split(":", 1)
        mod_file = installed_dir / (mod_rel.replace(".", "/") + ".py")
        if not mod_file.is_file():
            mod_file = installed_dir / f"{mod_rel}.py"
        if not mod_file.is_file():
            raise ExtensionExecutionError(
                f"Entry point module file '{mod_file}' not found for extension '{manifest.id}'.",
                extension_id=manifest.id,
            )

        try:
            spec = importlib.util.spec_from_file_location(f"ext_{manifest.id.replace('.', '_')}", mod_file)
            if not spec or not spec.loader:
                raise ExtensionExecutionError(f"Cannot load module spec for '{mod_file}'", extension_id=manifest.id)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            cls = getattr(module, cls_name)
            instance: BaseExtension = cls(manifest=manifest)

            instance.initialize(context)
            result = instance.execute(target_files, context)
            instance.teardown()
            return result

        except Exception as e:
            sanitized_err = self.gateway.sanitize_message(str(e))
            return ExtensionExecutionResult(
                success=False,
                error_message=f"In-process execution error: {sanitized_err}",
            )

    def _execute_subprocess(
        self,
        manifest: ExtensionManifest,
        installed_dir: Path,
        ep: EntryPointDefinition,
        target_files: list[Path],
        context: ExtensionExecutionContext,
        timeout_seconds: float,
    ) -> ExtensionExecutionResult:
        """Spawns an isolated Python worker subprocess with timeout and crash recovery."""
        mod_rel, cls_name = ep.target.split(":", 1)

        payload = {
            "extension_id": manifest.id,
            "module_path": str(installed_dir),
            "module_name": mod_rel,
            "class_name": cls_name,
            "target_files": [str(p) for p in target_files],
            "workspace_root": str(context.workspace_root),
            "config": context.config,
        }
        json_payload = json.dumps(payload)

        # Worker invocation argument vector
        cmd = [
            sys.executable,
            "-m",
            "packages.review.extensions.worker",
        ]

        # Subprocess environment with clean PYTHONPATH
        env = dict(os.environ)
        repo_root = str(Path(__file__).parent.parent.parent.parent.resolve())
        pythonpath_entries = [repo_root, str(installed_dir)]
        if "PYTHONPATH" in env:
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = ":".join(pythonpath_entries)

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )

            stdout_data, stderr_data = process.communicate(input=json_payload, timeout=timeout_seconds)

            if process.returncode != 0:
                err_msg = self.gateway.sanitize_message(stderr_data.strip() or f"Process returned code {process.returncode}")
                raise WorkerCrashError(
                    f"Extension worker crashed with exit code {process.returncode}: {err_msg}",
                    extension_id=manifest.id,
                )

            # Limit output payload size
            if len(stdout_data.encode("utf-8")) > MAX_OUTPUT_BYTES:
                raise ExtensionExecutionError(
                    f"Worker output exceeded maximum limit of {MAX_OUTPUT_BYTES} bytes.",
                    extension_id=manifest.id,
                )

            res_dict = json.loads(stdout_data)
            findings = [
                ExtensionFinding(
                    rule_id=f["rule_id"],
                    title=f["title"],
                    message=self.gateway.sanitize_message(f["message"]),
                    file_path=f["file_path"],
                    start_line=f["start_line"],
                    end_line=f.get("end_line"),
                    severity=f.get("severity", "INFO"),
                    suggestion=self.gateway.sanitize_message(f["suggestion"]) if f.get("suggestion") else None,
                    data=f.get("data", {}),
                )
                for f in res_dict.get("findings", [])
            ]

            return ExtensionExecutionResult(
                success=res_dict.get("success", True),
                findings=findings,
                metrics=res_dict.get("metrics", {}),
                error_message=res_dict.get("error_message"),
            )

        except subprocess.TimeoutExpired as e:
            process.kill()
            process.communicate()
            raise ExtensionExecutionError(
                f"Extension execution timed out after {timeout_seconds} seconds.",
                extension_id=manifest.id,
            ) from e
        except json.JSONDecodeError as e:
            raise ExtensionExecutionError(
                f"Worker returned malformed or non-JSON output: {e}",
                extension_id=manifest.id,
            ) from e
