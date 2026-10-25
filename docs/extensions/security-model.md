# Security Model & Sandboxing

The LogicFalcon Extension Platform implements a defense-in-depth security model to ensure untrusted or third-party extensions cannot compromise the host environment or user repositories.

---

## 1. Capabilities and Least Privilege

Extensions are denied access to sensitive operations by default. Every required operation must be explicitly declared in `extension.yaml`:

- **Static Declaration**: Capabilities are declared upfront in the manifest and displayed during `logicfalcon extension inspect` and `logicfalcon extension install --dry-run`.
- **Fail Closed**: Any attempt to perform an undeclared capability raises `CapabilityDeniedError` and emits an audit record in `CapabilityGateway.audit_log`.

---

## 2. Filesystem Path Containment

All filesystem interactions by extensions are sandboxed using `validate_contained_path`:

1. **Approved Roots**: Extensions may only access files contained within approved project roots.
2. **Traversal Prevention**: Relative path traversal attempts (such as `../../etc/passwd`) are strictly blocked via canonical path resolution (`.resolve()`).
3. **Protected Paths**: The following sensitive assets are permanently and non-negotiably blocked:
   - `/Users/livesh/AEGIS AI/render_schema.json`
   - Any path matching `/Users/livesh/AEGIS-Framework/**`
4. **Symlink Traversal**: Symlink escapes targeting files outside the workspace are blocked.

---

## 3. Server-Side Request Forgery (SSRF) Defense

For extensions requesting network access (`network:http`), `validate_safe_url` strictly blocks requests to:
- Loopback addresses (`127.0.0.0/8`, `::1`).
- RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- Link-local and Cloud Instance Metadata Services (IMDS) (`169.254.169.254`, `fe80::/10`).
- Non-HTTP/HTTPS schemes (e.g. `file://`, `gopher://`).
- DNS rebinding attacks: hostnames are resolved before connection and checked against prohibited IP subnets.

---

## 4. Cryptographic Parameter-Bound Approval for Mutations

For mutating actions (`fde:mutate`), declaring the capability alone is **not sufficient**. The extension must route execution through the FDE `PolicyGateway`:
- Every mutating step requires an explicit, cryptographically signed approval token computed over the mission ID, step ID, adapter, operation, and exact canonical parameters:
  $$\text{token} = \text{SHA256}(\text{mission\_id} : \text{step\_id} : \text{adapter\_id} : \text{operation} : \text{target} : \text{canonical\_params})$$
- Forged, replayed, or parameter-tampered approval tokens are immediately rejected with `ApprovalRequiredError`.

---

## 5. Secret Redaction & Sanitization

All output streams, error messages, and log records produced by extensions pass through `CapabilityGateway.sanitize_message`:
- API tokens (`sk-ant-*`, `ghp_*`, `AKIA*`, Bearer tokens) are automatically replaced with `[REDACTED_SECRET]` or `[REDACTED_TOKEN]`.
- Database credentials in connection strings are masked with `[REDACTED_PASSWORD]`.
- State files are saved with restricted permissions (`0o600`).
