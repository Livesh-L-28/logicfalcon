"""Command-line interface for the LogicFalcon Extension Platform."""

import argparse
import json
import sys
from pathlib import Path

from packages.review.extensions.compatibility import check_compatibility
from packages.review.extensions.errors import (
    ExtensionError,
    ManifestValidationError,
)
from packages.review.extensions.manager import ExtensionManager
from packages.review.extensions.manifest import parse_manifest
from packages.review.extensions.models import ExtensionStorageScope


def build_extension_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logicfalcon extension",
        description="Discover, inspect, validate, install, configure, monitor, update, and manage LogicFalcon extensions.",
    )
    subparsers = parser.add_subparsers(dest="action", help="Extension actions")

    # list
    list_p = subparsers.add_parser("list", help="List all installed extensions.")
    list_p.add_argument("--json", action="store_true", help="Output results in JSON format.")
    list_p.add_argument(
        "--scope",
        choices=["all", "user", "workspace"],
        default="all",
        help="Filter by storage scope (default: all).",
    )

    # inspect
    insp_p = subparsers.add_parser("inspect", help="Inspect metadata and permissions of an installed extension.")
    insp_p.add_argument("extension_id", help="Extension identifier (e.g., com.acme.perf-rules).")
    insp_p.add_argument("--json", action="store_true", help="Output results in JSON format.")

    # validate
    val_p = subparsers.add_parser("validate", help="Validate an extension manifest without executing code.")
    val_p.add_argument("path", help="Path to extension directory or manifest file.")
    val_p.add_argument("--json", action="store_true", help="Output results in JSON format.")

    # install
    inst_p = subparsers.add_parser("install", help="Plan and install an extension.")
    inst_p.add_argument("source", help="Path to extension source directory.")
    inst_p.add_argument("--workspace", action="store_true", help="Install into workspace scope (.logicfalcon/extensions).")
    inst_p.add_argument("--dry-run", action="store_true", help="Simulate installation and preview plan without mutating filesystem.")
    inst_p.add_argument("--json", action="store_true", help="Output installation plan in JSON format.")

    # enable
    en_p = subparsers.add_parser("enable", help="Enable an installed extension.")
    en_p.add_argument("extension_id", help="Extension identifier.")

    # disable
    dis_p = subparsers.add_parser("disable", help="Disable an extension without removing configuration or files.")
    dis_p.add_argument("extension_id", help="Extension identifier.")

    # update
    up_p = subparsers.add_parser("update", help="Update an extension from new source with automatic rollback snapshot.")
    up_p.add_argument("extension_id", help="Extension identifier.")
    up_p.add_argument("source", help="Path to updated extension source directory.")
    up_p.add_argument("--json", action="store_true", help="Output plan in JSON format.")

    # rollback
    rb_p = subparsers.add_parser("rollback", help="Roll back an extension to its prior version snapshot.")
    rb_p.add_argument("extension_id", help="Extension identifier.")

    # uninstall
    un_p = subparsers.add_parser("uninstall", help="Uninstall an extension.")
    un_p.add_argument("extension_id", help="Extension identifier.")
    un_p.add_argument("--purge", action="store_true", help="Purge saved extension configuration and state history.")

    # doctor
    doc_p = subparsers.add_parser("doctor", help="Run non-destructive diagnostic health checks on all installed extensions.")
    doc_p.add_argument("--json", action="store_true", help="Output health report in JSON format.")

    # search
    search_p = subparsers.add_parser("search", help="Search discovered local extensions.")
    search_p.add_argument("query", help="Search keyword.")
    search_p.add_argument("--json", action="store_true", help="Output search results in JSON format.")

    return parser


def run_extension_cli(args: list[str], manager: ExtensionManager | None = None) -> int:
    """Entry point for logicfalcon extension commands."""
    parser = build_extension_parser()
    if not args or args[0] in ("-h", "--help"):
        parser.print_help()
        return 0

    parsed = parser.parse_args(args)
    mgr = manager or ExtensionManager()

    try:
        if parsed.action == "list":
            items = mgr.discover()
            if parsed.scope != "all":
                target_scope = ExtensionStorageScope(parsed.scope)
                items = [it for it in items if it[1].scope == target_scope]

            if parsed.json:
                list_data = [
                    {
                        "id": m.id,
                        "name": m.name,
                        "version": m.version,
                        "description": m.description,
                        "scope": s.scope.value,
                        "enabled": s.enabled,
                        "state": s.state.value,
                        "installed_path": s.installed_path,
                    }
                    for m, s in items
                ]
                sys.stdout.write(json.dumps(list_data, indent=2) + "\n")
                return 0

            sys.stdout.write(f"\nInstalled LogicFalcon Extensions ({len(items)} found):\n")
            sys.stdout.write("-" * 80 + "\n")
            if not items:
                sys.stdout.write("  No extensions installed. Use 'logicfalcon extension install <source>' to install one.\n\n")
                return 0

            for m, s in items:
                status_icon = "🟢 ENABLED " if s.enabled else "⚪ DISABLED"
                sys.stdout.write(f"  {status_icon}  {m.id:<30} v{m.version:<8} [{s.scope.value}]\n")
                if m.description:
                    sys.stdout.write(f"              {m.description}\n")
            sys.stdout.write("\n")
            return 0

        elif parsed.action == "inspect":
            mgr.discover()
            entry = mgr.registry.get(parsed.extension_id)
            if not entry:
                sys.stderr.write(f"Error: Extension '{parsed.extension_id}' is not installed.\n")
                return 1

            if parsed.json:
                inspect_data = {
                    "manifest": entry.manifest.model_dump(mode="json"),
                    "state": entry.state.model_dump(mode="json"),
                }
                sys.stdout.write(json.dumps(inspect_data, indent=2) + "\n")
                return 0

            m = entry.manifest
            s = entry.state
            sys.stdout.write(f"\nExtension: {m.name} ({m.id})\n")
            sys.stdout.write("=" * 60 + "\n")
            sys.stdout.write(f"  Version:      {m.version}\n")
            sys.stdout.write(f"  Status:       {'ENABLED' if s.enabled else 'DISABLED'} ({s.state.value})\n")
            sys.stdout.write(f"  Scope:        {s.scope.value}\n")
            sys.stdout.write(f"  Path:         {s.installed_path}\n")
            sys.stdout.write(f"  Author:       {m.author or 'Unknown'}\n")
            sys.stdout.write(f"  License:      {m.license}\n")
            sys.stdout.write(f"  Description:  {m.description or 'None'}\n")
            sys.stdout.write("  Declared Capabilities:\n")
            if m.capabilities:
                for c in m.capabilities:
                    desc = f" ({c.description})" if c.description else ""
                    sys.stdout.write(f"    - {c.capability}{desc}\n")
            else:
                sys.stdout.write("    (none)\n")
            sys.stdout.write("\n")
            return 0

        elif parsed.action == "validate":
            src = Path(parsed.path)
            manifest_file = src if src.is_file() else (src / "extension.yaml" if (src / "extension.yaml").is_file() else src / "extension.json")
            if not manifest_file.is_file():
                sys.stderr.write(f"Error: No manifest found at '{parsed.path}'\n")
                return 1

            manifest = parse_manifest(manifest_file)
            is_compat, msg = check_compatibility(manifest)

            if parsed.json:
                validate_data = {
                    "valid": True,
                    "id": manifest.id,
                    "name": manifest.name,
                    "version": manifest.version,
                    "compatible": is_compat,
                    "compatibility_message": msg,
                    "capabilities": [c.capability for c in manifest.capabilities],
                }
                sys.stdout.write(json.dumps(validate_data, indent=2) + "\n")
                return 0

            sys.stdout.write(f"✓ Manifest '{manifest_file}' is syntactically valid.\n")
            sys.stdout.write(f"  ID:          {manifest.id}\n")
            sys.stdout.write(f"  Version:     {manifest.version}\n")
            sys.stdout.write(f"  Compatible:  {'YES' if is_compat else f'NO ({msg})'}\n")
            sys.stdout.write(f"  Capabilities: {len(manifest.capabilities)} declared\n")
            return 0

        elif parsed.action == "install":
            scope = ExtensionStorageScope.WORKSPACE if parsed.workspace else ExtensionStorageScope.USER
            plan = mgr.install(parsed.source, scope=scope, dry_run=parsed.dry_run)

            if parsed.json:
                install_data = {
                    "extension_id": plan.extension_id,
                    "name": plan.name,
                    "version": plan.version,
                    "scope": plan.target_scope.value,
                    "destination": str(plan.destination_path),
                    "compatible": plan.is_compatible,
                    "dry_run": parsed.dry_run,
                    "capabilities": plan.requested_capabilities,
                }
                sys.stdout.write(json.dumps(install_data, indent=2) + "\n")
                return 0

            prefix = "[DRY-RUN] " if parsed.dry_run else ""
            sys.stdout.write(f"\n{prefix}Installation Plan for {plan.name} ({plan.extension_id}):\n")
            sys.stdout.write(f"  Version:      {plan.version}\n")
            sys.stdout.write(f"  Target Scope: {plan.target_scope.value}\n")
            sys.stdout.write(f"  Destination:  {plan.destination_path}\n")
            sys.stdout.write(f"  Capabilities: {', '.join(plan.requested_capabilities) or 'none'}\n")
            if parsed.dry_run:
                sys.stdout.write("\nDry run complete. No files were modified.\n")
            else:
                sys.stdout.write(f"\n✓ Extension '{plan.extension_id}' successfully installed into {plan.target_scope.value} scope.\n")
                sys.stdout.write(f"  To enable, run: logicfalcon extension enable {plan.extension_id}\n\n")
            return 0

        elif parsed.action == "enable":
            state = mgr.enable(parsed.extension_id)
            sys.stdout.write(f"✓ Extension '{parsed.extension_id}' enabled successfully.\n")
            return 0

        elif parsed.action == "disable":
            state = mgr.disable(parsed.extension_id)
            sys.stdout.write(f"✓ Extension '{parsed.extension_id}' disabled successfully.\n")
            return 0

        elif parsed.action == "update":
            plan = mgr.update(parsed.extension_id, parsed.source)
            if parsed.json:
                update_data = {
                    "extension_id": plan.extension_id,
                    "updated_version": plan.version,
                    "scope": plan.target_scope.value,
                }
                sys.stdout.write(json.dumps(update_data, indent=2) + "\n")
                return 0
            sys.stdout.write(f"✓ Extension '{plan.extension_id}' updated to v{plan.version}.\n")
            sys.stdout.write("  Previous version snapshot retained for rollback.\n")
            return 0

        elif parsed.action == "rollback":
            state = mgr.rollback(parsed.extension_id)
            sys.stdout.write(f"✓ Extension '{parsed.extension_id}' rolled back to v{state.version}.\n")
            return 0

        elif parsed.action == "uninstall":
            mgr.uninstall(parsed.extension_id, purge_config=parsed.purge)
            purge_note = " (configuration purged)" if parsed.purge else " (configuration preserved)"
            sys.stdout.write(f"✓ Extension '{parsed.extension_id}' uninstalled successfully{purge_note}.\n")
            return 0

        elif parsed.action == "doctor":
            reports = mgr.diagnose()
            if parsed.json:
                sys.stdout.write(json.dumps([r.model_dump(mode="json") for r in reports], indent=2) + "\n")
                return 0

            sys.stdout.write(f"\nLogicFalcon Extension Diagnostic Doctor ({len(reports)} extensions inspected):\n")
            sys.stdout.write("=" * 70 + "\n")
            if not reports:
                sys.stdout.write("  No extensions installed.\n\n")
                return 0

            all_ok = True
            for r in reports:
                status_icon = "🟢 PASS" if r.healthy else "🔴 FAIL"
                if not r.healthy:
                    all_ok = False
                sys.stdout.write(f"[{status_icon}] {r.extension_id} v{r.version} ({r.state.value})\n")
                for chk in r.checks:
                    chk_icon = "✓" if chk["passed"] else "✗"
                    sys.stdout.write(f"       {chk_icon} {chk['probe']}: {chk['message']}\n")
            sys.stdout.write("-" * 70 + "\n")
            sys.stdout.write(f"Diagnostic result: {'All extensions healthy' if all_ok else 'Issues detected'}\n\n")
            return 0 if all_ok else 1

        elif parsed.action == "search":
            mgr.discover()
            q = parsed.query.lower()
            matches = [
                entry
                for entry in mgr.registry.list_all()
                if q in entry.manifest.id.lower() or q in entry.manifest.name.lower() or q in entry.manifest.description.lower()
            ]

            if parsed.json:
                search_data = [
                    {
                        "id": e.manifest.id,
                        "name": e.manifest.name,
                        "version": e.manifest.version,
                        "description": e.manifest.description,
                        "enabled": e.state.enabled,
                    }
                    for e in matches
                ]
                sys.stdout.write(json.dumps(search_data, indent=2) + "\n")
                return 0

            sys.stdout.write(f"\nSearch results for '{parsed.query}' ({len(matches)} matches):\n")
            sys.stdout.write("-" * 65 + "\n")
            for e in matches:
                sys.stdout.write(f"  {e.manifest.id} (v{e.manifest.version}): {e.manifest.name}\n")
                if e.manifest.description:
                    sys.stdout.write(f"    {e.manifest.description}\n")
            sys.stdout.write("\n")
            return 0

        parser.print_help()
        return 0

    except (ExtensionError, ManifestValidationError) as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"Unexpected extension error: {e}\n")
        return 2
