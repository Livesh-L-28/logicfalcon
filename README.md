# LogicFalcon — Fast, precise engineering intelligence.

> **LogicFalcon, powered by AEGIS AI**  
> LogicFalcon is an AI-powered software engineering intelligence platform for evidence-grounded code review, repository analysis, change-impact assessment, root-cause analysis, and safe fix proposals. Powered by AEGIS AI.

---

## Quickstart & Installation

### 1. Installation via pip

```bash
pip install logicfalcon
```

### 2. 30-Second Terminal Health Check

```bash
# One-liner verification
python3 -c "import logicfalcon; print(f'LogicFalcon {logicfalcon.__version__} ready.')" && logicfalcon doctor
```

### 3. Developer CLI Usage

```bash
# Verify environment and AST analyzer capabilities
logicfalcon doctor

# Run deterministic code review on local git diff (optionally enriched with architecture context)
logicfalcon review --repo . --with-re-context

# Machine-readable JSON or SARIF v2.1.0 output for CI pipelines with baseline suppression
logicfalcon review --repo . --format sarif --severity-threshold HIGH --baseline .logicfalcon-baseline.json

# Analyze repository architecture (cycles, coupling instability, boundary violations)
logicfalcon architecture --repo . --format text --max-cycles 10

# Reverse engineer repository inventory, APIs, data models, call graphs, and run integrated review
logicfalcon reverse-engineer --repo . --format markdown --with-review --max-depth 15 --output-file REVERSE_ENGINEERING.md

# Change impact analysis & predictive test selection on working tree or git revisions
logicfalcon impact --repo . --unstaged --format markdown --output-file IMPACT.md

# CI change impact gate: fail if risk score reaches HIGH or CRITICAL
logicfalcon impact --repo . --base origin/main --target HEAD --format json --fail-on-risk HIGH

# Continuous engineering intelligence & historical health tracking
logicfalcon history snapshot --repo .
logicfalcon history list
logicfalcon history compare --repo .
logicfalcon history trends --repo . --last 10
logicfalcon history debt --repo .
logicfalcon history policy --repo . --config .logicfalcon-policy.json
logicfalcon history prune --keep-last 20

# Forward Deployment Engineering (FDE) — discovery, preflight, planning, runbooks, and controlled execution
logicfalcon fde inspect --repo .
logicfalcon fde preflight --repo .
logicfalcon fde plan --repo . --operation deploy --output plan.json
logicfalcon fde runbook --mission-file plan.json --output-format markdown
logicfalcon fde run --mission-file plan.json --dry-run
logicfalcon fde run --mission-file plan.json --approved --approval-token <TOKEN>

# Launch stdio Model Context Protocol (MCP) server for AI coding agents
logicfalcon mcp
```

### 3. Python SDK Usage

```python
from pathlib import Path
from logicfalcon import (
    LocalReviewEngine,
    ReviewConfig,
    analyze_architecture,
    reverse_engineer,
    reverse_engineer_with_review,
    analyze_impact,
    analyze_impact_with_review,
    capture_snapshot,
    compare_snapshots,
    analyze_trends,
    estimate_debt,
    evaluate_history_policy,
)

# 1. Deterministic Code Review with Architecture Context
config = ReviewConfig(
    max_file_size_bytes=1_000_000,
    per_file_timeout_seconds=10.0,
    include_re_context=True,  # Enriches findings with architectural component, blast radius & routes
    enable_ai_review=False,   # Deterministic static analysis by default
)
engine = LocalReviewEngine(repo_root=Path("."), config=config)
report = engine.review_local_git_diff()
print(f"Scanned {len(report.files_reviewed)} files. Found {len(report.findings)} issues.")

# 2. Architecture & Dependency Health Analysis
arch_report = analyze_architecture(repo_root=Path("."), max_cycles=10)
print(f"Architecture Score: {arch_report.health_score}/100")
print(f"Detected {len(arch_report.cycles)} circular dependencies.")

# 3. Reverse Engineering Intelligence with Integrated Review
re_report = reverse_engineer_with_review(repo_root=Path("."))
print(f"Scanned {re_report.inventory.total_files} files across {len(re_report.inventory.languages)} languages.")
print(f"Discovered {re_report.api_inventory.total_routes} API routes and {re_report.data_model_inventory.total_models} data models.")
if re_report.review_summary:
    print(f"Integrated review findings: {re_report.review_summary.get('total_findings', 0)}")

# 4. Change Impact Analysis & Predictive Test Selection
impact_report = analyze_impact(repo_root=Path("."), unstaged=True)
print(f"Impact Risk Level: {impact_report.risk_level} (Score: {impact_report.risk_score}/100)")
print(f"Impacted Entities: {len(impact_report.impacted_entities)}")
print(f"Recommended Tests: {[t.test_file for t in impact_report.recommended_tests]}")

# 5. Continuous Engineering Intelligence & Historical Health Tracking
snap = capture_snapshot(repo_root=Path("."), persist=True)
print(f"Captured snapshot {snap.id} (Health: {snap.metrics.health_score}/100, Debt: {snap.metrics.technical_debt_score} pts)")
trends = analyze_trends(repo_root=Path("."))
print(f"Repository Health Trend: {trends.health_direction} | Debt Trend: {trends.debt_direction}")

# 6. Forward Deployment Engineering (FDE)
from logicfalcon import fde_inspect, fde_preflight, fde_plan, fde_generate_runbook, fde_run_mission

inventory = fde_inspect(repo_root=Path("."))
print(f"Frameworks: {inventory.frameworks}, Ports: {inventory.declared_ports}, DBs: {inventory.database_types}")

preflight_report = fde_preflight(repo_root=Path("."))
print(f"Preflight status: {preflight_report.status} ({len(preflight_report.findings)} findings)")

mission = fde_plan(repo_root=Path("."))
print(f"Planned mission {mission.id} with {len(mission.steps)} steps.")

runbook = fde_generate_runbook(mission=mission, inventory=inventory)
print(f"Generated runbook with {len(runbook.ordered_instructions)} instructions.")
```


### 4. Deterministic Rule Catalog

LogicFalcon operates completely offline and deterministically without hallucination risk:

| Rule Code | Category | Name | Detection |
| :--- | :--- | :--- | :--- |
| `SEC-001` | Security | Dynamic Code Execution | `eval()` and `exec()` invocations |
| `SEC-002` | Security | Unsafe Shell / Command Execution | `subprocess` with `shell=True`, `os.system()`, and `os.popen()` |
| `SEC-003` | Security | Hardcoded Credential | API keys, private tokens, passwords (redacted in evidence) |
| `SEC-004` | Security | Insecure Deserialization | `pickle.loads()`, `marshal.loads()`, and `shelve.open()` usage |
| `SEC-005` | Security | Syntax Error Detection | Unparsable source files |
| `SEC-008` | Security | Insecure PyYAML Deserialization | `yaml.load()` without `SafeLoader` |
| `SEC-009` | Security | Insecure Archive Extraction | `extractall()` without safe directory containment |
| `SEC-010` | Security | XML Entity Expansion (XXE) | Standard library XML parsers susceptible to entity expansion |
| `REL-002` | Reliability | Missing Network Timeout | `requests`, `httpx`, `urllib` calls without explicit timeout |
| `QUAL-001` | Quality | Broad Exception Suppression | Bare `except:` or `except Exception: pass` without logging |
| `DEP-001` | Security | Known Dependency Advisory | Pinned Python (`requirements.txt`, `pyproject.toml`) and JS/TS (`package.json`) matching local CVE database |
| `ARCH-001` | Architecture | Circular Dependency | Direct or indirect import cycles detected via DFS / Tarjan SCC |
| `ARCH-002` | Architecture | Layer Boundary Violation | Illegal cross-tier imports violating architecture boundaries |

---

## Forward Deployment Engineering (FDE)

LogicFalcon v0.1.4 introduces **Forward Deployment Engineering (FDE)** — a modular, secure, deterministic subsystem designed to bridge the gap between static repository intelligence and production operational deployment readiness.

### Key Capabilities
- **Deployment & Service Discovery**: Deterministic scanning of repositories to catalog framework services, exposed ports, database dependencies, and container definitions without running code.
- **Preflight Probes**: Bounded, non-destructive environmental health checks verifying port availability, runtime versions, DNS resolution, and required environment configurations.
- **Safe Adapters & Registry**: Standardized, least-privilege interfaces for System (non-shell subprocess execution), HTTP (SSRF-protected, cloud metadata IP blocking, TLS verification), Docker, PostgreSQL, MCP, and AWS.
- **Policy Gateway & Approval Security**: Strict state-machine orchestration with cryptographic parameter-bound SHA-256 approval tokens preventing privilege escalation or token reuse.
- **Postcondition Verification**: Declarative verification validating HTTP response codes, JSON body values, and port bindings with deterministic pass/fail results.
- **Failure Diagnosis & Atomic Checkpointing**: Ranked root-cause hypotheses for mission step failures and atomic snapshotting (`0o600` permissions) with recursive credential redaction.
- **Handover Runbooks**: Automated Markdown and machine-readable JSON operational handover runbooks with sanitized commands.

For comprehensive technical documentation, refer to:
- [FDE Overview & Getting Started](docs/fde/README.md)
- [FDE Architecture & Security Model](docs/fde/architecture.md)
- [FDE CLI Reference](docs/fde/cli-reference.md)
- [FDE SDK Reference](docs/fde/sdk-reference.md)

---

## Platform Engine (AEGIS AI Foundation)

LogicFalcon's core reasoning, multi-language AST comprehension, and autonomous reliability engines are built on the **AEGIS AI** platform architecture.

> **Engine Status: Phase 7 — Autonomous Reliability + Evaluation + Production Hardening COMPLETE (CURRENT)**

> **Phase 7 Scope Note:** Phase 7 concludes the roadmap by delivering bounded autonomous reliability under deterministic safety controls: bounded agent execution loops with strict tool and cost budgets, multi-tiered autonomy levels (`LEVEL_0` through `LEVEL_3`), emergency stop kill switches, change freeze mechanisms, autonomy circuit breakers, continuous evaluation against golden and adversarial datasets with strict release gates, SLO and error budget tracking, and operational learning from validated incidents without self-modifying code or policies.


---

## Unified System Model

```text
                    AEGIS INTELLIGENCE
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
      SYSTEM            CODE            KNOWLEDGE
   INTELLIGENCE      INTELLIGENCE      INTELLIGENCE
          │                │                │
          ▼                ▼                ▼
      Services          Git             Docs
      Dependencies      Files           Runbooks
      Environments      Symbols         Incidents
      Deployments       Commits         Postmortems
      Telemetry         AST             Architecture
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                  UNIFIED SYSTEM MODEL
```

---

## Intelligence Capabilities
- **System Intelligence**: Runtime topology discovery, typed dependency relationships (`HTTP`, `DATABASE`, `CACHE`), machine-readable graph API (`GET /api/v1/intelligence/dependency-graph`).
- **Code Intelligence**: Static AST parsing (classes, methods, functions, signatures, docstrings, imports), SHA256 incremental indexing, secret redaction (`[REDACTED_SECRET]`), symbol search (`POST /api/v1/intelligence/code/search`).
- **Knowledge Intelligence**: Section-based document chunking, 64-dimensional unit vector embeddings, hybrid keyword + dense vector retrieval with score normalization (`POST /api/v1/intelligence/knowledge/search`).
- **Unified Context API**: Assembles full service context across topology, symbols, and operational documentation (`GET /api/v1/intelligence/services/{service}/context`).

---

## Public Portfolio Architecture (Render All-in-One Deployment)

```text
                               GitHub Repository
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
           Render Static Site                  Render Web Service
        React 18 + Vite Frontend               FastAPI Backend API
        (aegis-ai-web.onrender.com)        (aegis-ai-api.onrender.com)
                      │                                 │
                      │  (REST API & SSE stream)        │
                      └────────────────►────────────────┤
                                                        │
                                     ┌──────────────────┼──────────────────┐
                                     ▼                  ▼                  ▼
                                Render Postgres       Redis          Object Storage
                                  + pgvector    (Upstash / Aiven)   (Cloudflare R2 / S3)
```

---

## Live Demo & Documentation

### Deployed Portfolio URLs

* **Deployment Documentation**: [`docs/deployment/public-demo.md`](docs/deployment/public-demo.md)
* **Render Blueprint**: [`render.yaml`](render.yaml) (1-Click deployment for Frontend + Backend + PostgreSQL)
* **Frontend**: Configured for Render Static Site (`apps/web`, SPA rewrite `/* -> /index.html`, `VITE_API_BASE_URL`) or Vercel
* **API**: Configured for Render Docker Web Service with dynamic `$PORT` and container health checks

---

## Local Quickstart (Full Docker Compose Environment)

To run the complete AEGIS ecosystem locally including Prometheus, Grafana, Loki, MinIO, and 4 simulated microservices:

```bash
# 1. Clone repository
git clone <repository_url>
cd "AEGIS AI"

# 2. Configure environment
cp .env.example .env

# 3. Start complete local infrastructure
docker compose up --build -d

# 4. Open Command Center
open http://localhost:5173
```

---

## Interactive Recruiter Demo Scenario

Experience the complete **Observe → Reason → Propose → Approve → Sandbox Execute → Validate** autonomous reliability lifecycle:

1. **Open Dashboard**: Navigate to the Operational Overview.
2. **Trigger Incident (INC-001)**: Under *Canonical Fault Scenarios*, click **Inject Fault** on scenario `SCEN-001` (Redis Connection Exhaustion) or `SCEN-002` (Downstream Latency Spike).
3. **Observe Incident**: View the newly detected incident in the *Live Incident Pipeline* with its severity and affected service.
4. **Run AI Investigation**: Click **Investigate** to open the Incident Deep Dive. Click **Run AI Investigation** to correlate telemetry, git history, and runbooks.
5. **Inspect Evidence & Causal Graph**: Review multi-modal evidence signals and the determined root cause.
6. **Propose Remediation**: Click **Propose AI Remediation** to synthesize a bounded, typed action plan.
7. **Review Risk & Blast Radius**: Inspect calculated risk levels and affected services.
8. **Human Approval**: Click **Approve Action** to cryptographically authorize the plan.
9. **Sandbox Execution**: Click **Execute in Sandbox** to safely apply the fix to the simulated environment.
10. **Validate & Audit**: Inspect the automated post-flight verification check and the immutable entry recorded in the Audit log.

---

## Verification & Quality Gates

```bash
# Code formatting & lint check
uv run ruff check .

# Strict static type check
uv run mypy --explicit-package-bases logicfalcon aegis apps packages tests

# Automated test suite
uv run pytest tests/ -q
```

---

## License & Trademarks

- **Software License**: LogicFalcon is open-source software licensed under the **Apache License, Version 2.0**. See the authoritative license terms in [`LICENSE`](LICENSE).
- **Platform Foundation**: LogicFalcon is powered by the **AEGIS AI** engineering intelligence platform.
- **Copyright & Attribution**: Copyright 2026 LogicFalcon Authors & Contributors (powered by AEGIS AI). Third-party dependencies retain their respective permissive licenses (MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause).
- **Trademarks**: The LogicFalcon name and logo are product brand identifiers separate from the software copyright license and are not licensed for unrestricted trademark use.
- **Contributing**: Contributions are subject to the terms in [`CONTRIBUTING.md`](CONTRIBUTING.md).

