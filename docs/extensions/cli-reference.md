# CLI Reference: `logicfalcon extension`

Unified command-line interface for managing LogicFalcon runtime extensions.

---

## Commands

### `list`
Lists all installed extensions across scopes.

```bash
logicfalcon extension list [--json] [--scope {all,user,workspace}]
```

- `--json`: Output machine-readable JSON array.
- `--scope`: Filter by scope (`user`, `workspace`, or `all`). Default: `all`.

---

### `inspect`
Displays detailed manifest metadata, declared capabilities, and runtime status for an extension.

```bash
logicfalcon extension inspect <extension_id> [--json]
```

---

### `validate`
Validates an extension manifest without importing or executing any code.

```bash
logicfalcon extension validate <path> [--json]
```

- `<path>`: Path to extension directory or manifest file (`extension.yaml` / `extension.json`).

---

### `install`
Plans and installs an extension from a source directory.

```bash
logicfalcon extension install <source> [--workspace] [--dry-run] [--json]
```

- `--workspace`: Install into current repository's `.logicfalcon/extensions/`. Default: user scope (`~/.logicfalcon/extensions/`).
- `--dry-run`: Previews the installation plan, verifying compatibility and capabilities without modifying any files.
- `--json`: Outputs installation plan as JSON.

---

### `enable`
Enables an installed extension for active review passes.

```bash
logicfalcon extension enable <extension_id>
```

---

### `disable`
Disables an extension without deleting its files or configuration.

```bash
logicfalcon extension disable <extension_id>
```

---

### `update`
Updates an installed extension to a newer source version, retaining a rollback snapshot.

```bash
logicfalcon extension update <extension_id> <source_path> [--json]
```

---

### `rollback`
Reverts an updated extension to its previous version snapshot.

```bash
logicfalcon extension rollback <extension_id>
```

---

### `uninstall`
Uninstalls an extension. Preserves configuration in state file by default.

```bash
logicfalcon extension uninstall <extension_id> [--purge]
```

- `--purge`: Completely removes saved configuration and state history.

---

### `doctor`
Runs non-destructive health checks across all installed extensions (verifying filesystem directories, manifest validity, and host compatibility).

```bash
logicfalcon extension doctor [--json]
```

---

### `search`
Searches installed and local extensions by keyword.

```bash
logicfalcon extension search <query> [--json]
```
