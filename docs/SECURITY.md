# DevMatrix AI — Security Architecture & Privacy Policy

## 1. Ethical AI & Workforce Privacy Charter

DevMatrix AI adheres to strict ethical principles regarding workforce intelligence and employee monitoring:

1. **Zero Covert Surveillance**:
   - The platform never collects, stores, or processes keystrokes, mouse clicks, webcam captures, audio feeds, desktop screenshots, or continuous time-spent indicators.
   - Productivity is never equated with raw hours online or activity volume.
2. **Contextual Evaluation**:
   - Delivery performance evaluates verified deliverables, reviewed code, accepted pull requests, and documented blockers within the context of task complexity and dependency shifts.
3. **Right to Challenge & Correct**:
   - Every contributor has access to their recorded work metrics and a formal workflow (`correction_requests`) to request rectification of inaccurate records.
4. **No Automated Adverse Action**:
   - Recommendations are advisory decision support. Automated hiring, termination, or formal reprimands driven solely by AI algorithms are strictly prohibited.

---

## 2. Authentication & Authorization (RBAC)

- **Password Security**: Passwords are hashed using `bcrypt` with random 12-round salts. Plaintext passwords never touch logs, databases, or responses.
- **JWT Session Tokens**: Standard RFC 7519 JWT signed with HMAC-SHA256 (`HS256`). Tokens carry expiration timestamps (`exp`, 24h default) and user identity claims.
- **Server-Side Enforcement**:
  - Permissions are validated inside FastAPI dependency injection handlers (`require_role(...)`).
  - Hiding frontend buttons is never relied upon as security.
- **Role Hierarchy**:
  - `tenant_admin`: User provisioning, tenant settings, diagnostics, retention policies, and immutable audit logs.
  - `delivery_manager`: Project intake, requirement baseline approval, WBS generation, cost estimation, risk review, workforce allocation, and report compilation.
  - `project_lead`: WBS task management, dependencies, progress tracking, and blocker escalations.
  - `contributor`: View assigned deliverables, submit logged progress and work notes, and submit record corrections.

---

## 3. Multi-Tenant Data Isolation

- Every table (except system-wide reference data) contains an indexed `tenant_id` foreign key.
- All ORM queries in repository and service layers filter strictly by `tenant_id == current_user.tenant_id`.
- Cross-tenant record leakage is mathematically prevented at the database query level.

---

## 4. File Intake & Storage Security

- **UUID Storage Names**: Uploaded documents are saved under random UUID v4 filenames in `storage/uploads/` to prevent directory traversal or file overwrite attacks.
- **Magic Byte Validation**: File headers are inspected via byte signatures (e.g. `%PDF-` for PDF, `PK\x03\x04` for DOCX/XLSX). Files with mismatched extensions and binary headers are rejected.
- **Streaming Size Enforcement**: Chunked stream consumption terminates uploads that exceed the 15 MB limit immediately before consuming disk space.
- **Private Vaults**: Storage directories are never mounted as public static assets. Downloads require JWT authentication and tenant ownership verification.

---

## 5. Secret Management & AI Provider Telemetry Sanitization

- **Zero Secret Commits**: Real API keys, tokens, and DB passwords are never committed to git.
- **Sanitized Telemetry**: Provider call diagnostics record only provider name, model identifier, latency, token usage, and sanitized status codes. Raw prompts, document text, and authorization headers are scrubbed from logs and database columns.
- **Prompt Injection Defense**: Content inside uploaded files is treated strictly as untrusted document text. System prompts instruct models to ignore embedded instructions attempting to override extraction instructions.
