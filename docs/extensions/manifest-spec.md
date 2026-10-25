# Extension Manifest Specification

Every LogicFalcon extension requires an `extension.yaml` or `extension.json` manifest located at the root of the extension directory.

---

## Example `extension.yaml`

```yaml
schema_version: "1.0.0"
id: "com.acme.perf-rules"
name: "ACME Performance Rules"
version: "1.0.0"
description: "Deterministic AST checks for memory leaks and performance bottlenecks."
author: "ACME Engineering"
license: "Apache-2.0"

compatibility:
  logicfalcon: ">=0.1.4"
  python: ">=3.12"

capabilities:
  - capability: "project:read"
    description: "Read repository source files for inspection"
  - capability: "project:analyze"
    description: "Generate AST and static findings"

entry_points:
  analyzer:
    - name: "default"
      target: "src.analyzer:AcmePerfAnalyzer"
      execution_mode: "in_process"

configuration_schema:
  type: "object"
  properties:
    max_complexity:
      type: "integer"
      default: 15
```

---

## Schema Fields

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `schema_version` | string | Yes | Manifest schema version (e.g. `"1.0.0"`). |
| `id` | string | Yes | Unique reverse-DNS lowercase identifier (e.g. `com.acme.perf-rules`). |
| `name` | string | Yes | Human-readable extension display name. |
| `version` | string | Yes | SemVer 2.0 compliant version string (e.g. `1.0.0`). |
| `description` | string | No | Explanation of functionality. |
| `author` | string | No | Author or organization name. |
| `license` | string | No | SPDX license identifier (default: `"Apache-2.0"`). |
| `compatibility` | object | No | Minimum versions required for `logicfalcon` and `python`. |
| `capabilities` | list | Yes | Declared permissions requested by the extension. |
| `entry_points` | object | Yes | Mapping of category to entry point definitions. |
| `configuration_schema` | object | No | JSON Schema defining customizable options. |

---

## Recognized Capabilities

| Capability | Category | Description |
| :--- | :--- | :--- |
| `project:read` | Read-only | Read source files within the approved project root. |
| `project:analyze` | Read-only | Parse AST and produce findings. |
| `env:read` | Read-only | Inspect allowed environment variable metadata. |
| `network:http` | Network | Perform outbound HTTP requests (SSRF protected). |
| `fde:mutate` | Mutating | Perform modifying operations via FDE adapters (requires PolicyGateway approval token). |
