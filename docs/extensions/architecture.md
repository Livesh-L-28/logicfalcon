# Architecture & Execution Isolation

The **LogicFalcon Extension Platform** uses a layered, defense-in-depth architecture designed for zero regressions, strict security boundaries, and reliable recovery.

---

## 1. Architectural Layers

```mermaid
graph TD
    CLI[LogicFalcon CLI: logicfalcon extension ...] --> Manager[ExtensionManager]
    SDK[LogicFalcon SDK: logicfalcon.sdk] --> Manager
    
    Manager --> Registry[ExtensionRegistry (In-Memory Lookup)]
    Manager --> Storage[Filesystem Storage Scopes (User & Workspace)]
    Manager --> Compatibility[Compatibility Engine (SemVer & Python)]
    
    Manager --> Runner[ExtensionRunner]
    Runner --> CapGate[CapabilityGateway & Path Sandbox]
    
    CapGate --> ModeCheck{Execution Mode}
    ModeCheck -->|in_process| InProcess[Dynamic Python Loader]
    ModeCheck -->|subprocess_worker| Worker[Isolated Worker Subprocess (IPC over Stdin/Stdout)]
    
    CapGate --> PolicyGate[FDE PolicyGateway (Cryptographic Parameter-Bound Tokens)]
```

### Storage Scopes & Precedence
1. **Workspace Scope (`.logicfalcon/extensions/`)**: Project-specific rules and configurations tracked within a repository. Takes precedence over user-scope extensions when an identifier collides.
2. **User Scope (`~/.logicfalcon/extensions/`)**: Developer-specific extensions available across all local repositories.
3. **Built-in Reference (`packages/review/extensions/reference/`)**: Core reference extensions shipped with the package (e.g., `org.logicfalcon.todo-analyzer`).

---

## 2. Dual Execution Modes

Extensions declare their intended execution mode in `extension.yaml`:

### Mode A: In-Process (`in_process`)
- **Use Case**: Lightweight, deterministic static analysis and AST rules with zero external dependencies.
- **Benefits**: Near-zero invocation overhead, sub-millisecond execution.
- **Safety**: Manifest capability validation and path containment are strictly enforced.

### Mode B: Subprocess Worker (`subprocess_worker`)
- **Use Case**: Extensions requiring independent dependencies, heavy compute, or fault isolation.
- **Benefits**:
  - Independent process group.
  - Strict timeout bounds (default 30 seconds, configurable).
  - Out-of-memory or crash isolation: a worker crash (`WorkerCrashError`) never brings down the host LogicFalcon process.
  - Output payload size cap (5 MB) preventing memory exhaustion.
- **IPC Protocol**: Strict JSON request/response over standard input and standard output. No shell interpolation (`shell=False` argument vectors exclusively).

---

## 3. Reliability & Atomic State Transitions

- **Atomic Staging**: Extensions are unpacked and validated in a staging directory (`ext_<id>_<uuid>`) within the target scope before being atomically renamed into position.
- **Rollback Snapshots**: During an update, the prior working version is preserved in `<id>.backup`. If an update fails mid-flight or if an operator invokes `logicfalcon extension rollback <id>`, the prior state is instantly restored.
- **Config Preservation**: Uninstalling an extension (`logicfalcon extension uninstall <id>`) deletes extension code while preserving operator configuration in `state.json` unless `--purge` is explicitly specified.
