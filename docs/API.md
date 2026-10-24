# DevMatrix AI — API Specification & Integration Contract

## Overview

The DevMatrix AI backend provides a predictable RESTful API designed with versionable resource endpoints, strict Pydantic v2 validation, JWT authentication, and server-side role-based access control (RBAC).

All requests and responses use JSON (except multipart document uploads and binary PDF report streaming). All endpoints enforce tenant isolation via the authenticated user's JWT token.

Base URL: `http://localhost:8000/api`

---

## Standard Error Response Contract

All errors return a machine-readable schema:

```json
{
  "code": "ERROR_CODE_STRING",
  "message": "Human-readable sanitized explanation",
  "details": {},
  "request_id": "uuid-v4-trace-id"
}
```

---

## Endpoints

### 1. Health & Readiness
- `GET /health`
  - Returns backend health, database connection state, and storage directories readiness.

### 2. Module 1: Authentication & Profiles
- `POST /auth/login`
  - Request: `{"email": "...", "password": "..."}`
  - Response: `{"access_token": "...", "token_type": "bearer", "expires_in_minutes": 1440, "user": {...}}`
- `GET /auth/me`
  - Headers: `Authorization: Bearer <token>`
  - Response: User profile with `id`, `tenant_id`, `tenant_name`, `email`, `full_name`, `role`.

### 3. Module 2: Project Intake & Document Vault
- `GET /documents?project_id={id}`
  - List cataloged documents with extraction metadata, word counts, and page info.
- `GET /documents/{doc_id}`
  - Retrieve detailed document metadata and extracted text.
- `POST /documents/upload`
  - Content-Type: `multipart/form-data`
  - Form fields: `file` (binary), `project_id` (optional).
  - Validation: Magic byte file signature, supported format extension, 15 MB streaming limit.
- `DELETE /documents/{doc_id}`
  - Safely deletes document and cleaned associated files with audit logging.

### 4. Module 3: AI Requirements & Observable Jobs
- `POST /jobs/extract/{doc_id}`
  - Initiates background async extraction job.
  - Returns: `{"id": "job-...", "status": "queued", "progress_pct": 0}`
- `GET /jobs/{job_id}`
  - Returns observable job lifecycle: `status` (`queued`, `running`, `succeeded`, `failed`, `cancelled`), `progress_pct`, `error_message`, `telemetry`.
- `POST /requirements/extract/{doc_id}`
  - Synchronous / direct trigger with multi-provider sequential fallback (Gemini 2.5 Flash -> NVIDIA NIM -> Offline Mock).
- `GET /requirements/document/{doc_id}`
  - Lists extraction drafts associated with the document.
- `PATCH /requirements/{draft_id}/review`
  - Manager review decision: `review_status` (`approved`, `rejected`, `pending_review`), `manager_notes`.
- `POST /requirements/draft/{draft_id}/approve`
  - Delivery Manager baseline approval. Promotes draft to immutable versioned baseline (`v1`, `v2`).
- `GET /requirements/baseline/{project_id}`
  - Retrieves active approved requirements baseline.

### 5. Module 4: Work Breakdown Structure (WBS)
- `POST /wbs/generate/{project_id}`
  - Generates candidate WBS deliverables and tasks from approved requirements baseline.
- `GET /wbs/{project_id}`
  - Returns complete topologically sorted task graph, total PERT hours, and cycle validation status.
- `POST /wbs/task`
  - Creates a custom or edited task with three-point estimate (`optimistic`, `most_likely`, `pessimistic`).
- `POST /wbs/dependency`
  - Links predecessor to successor task. Rejects circular dependencies via DFS cycle detection.

### 6. Module 5: Deterministic Estimation & CPM Schedule
- `POST /estimation/calculate/{project_id}`
  - Computes three-point PERT effort `(O + 4M + P)/6`, CPM critical path sequence, role labor costs, and contingency buffer.
- `GET /estimation/{project_id}`
  - Retrieves active project estimate snapshot and role breakdown.

### 7. Module 6: Feasibility & Risk Intelligence
- `POST /risks/evaluate/{project_id}`
  - Executes 7-dimension feasibility assessment and builds $L \times I$ risk register.
- `GET /risks/{project_id}`
  - Retrieves feasibility dimensions, limitations, and risk entries.

### 8. Module 7: Workforce Intelligence & Team Allocation
- `GET /workforce`
  - Lists tenant workforce directory with skills, experience, standard rate, and available capacity.
- `POST /workforce/recommend/{project_id}`
  - Computes explainable 4-factor ranking: Skill Fit (40%), Availability (30%), Experience (20%), Workload (10%).
- `POST /workforce/recommendations/{rec_id}/approve`
  - Manager approves proposed assignment.

### 9. Module 8: Project Execution & Tracking
- `GET /execution/summary/{project_id}`
  - Returns completion percentage, effort burnup, milestones, and active blockers.
- `POST /execution/task-update`
  - Contributor or Lead logs verified hours, updates task status (`not_started`, `in_progress`, `blocked`, `in_review`, `completed`), and flags blockers.

### 10. Modules 9 & 10: Delivery Analytics & Calibration
- `GET /analytics/delivery/{project_id}`
  - Returns planned vs. actual effort variance, deliverable velocity, and fair metrics policy statement.
- `GET /analytics/historical`
  - Returns validated historical project outcomes, mean variances, and composite calibration factor ($N \ge 5$ policy).

### 11. Module 12: Professional PDF Reporting
- `POST /reports/generate/{project_id}`
  - Compiles the 15-section Executive Project Delivery Book PDF using ReportLab from stored database records.
- `GET /reports/{project_id}`
  - Lists archived report snapshots.
- `GET /reports/{report_id}/download`
  - Streams binary PDF file (`application/pdf`) with `Content-Disposition: attachment; filename="...pdf"`.

### 12. Module 13: Administration & Governance
- `GET /admin/users`
  - Lists tenant users and assigned RBAC roles.
- `GET /admin/tenant`
  - Retrieves tenant organization details, currency, default contingency, and retention policy.
- `GET /admin/audit-logs`
  - Retrieves append-only immutable audit log events.
- `GET /admin/diagnostics`
  - Returns non-sensitive system diagnostics: DB connectivity, storage directory verification, and provider status.
