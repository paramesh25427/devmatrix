# DevMatrix AI — Database Architecture & Schema Documentation

## Database Overview

DevMatrix AI utilizes a normalized, PostgreSQL-compatible relational database schema managed via **SQLAlchemy 2.0** ORM and **Alembic** migrations. For local single-machine development, the database resolves to a single canonical SQLite file:

Canonical DB Path: `E:\hackthon\Devmatrix\data\devmatrix.db`

All ambiguous relative path resolutions (`sqlite:///./devmatrix.db`) have been eliminated. In production, the schema deploys identically to PostgreSQL with zero ORM code alterations.

---

## Entity Relationship Overview

The schema is divided into 22 normalized models enforcing multi-tenant isolation, foreign keys, and indexes:

### 1. Identity & Tenancy
- **`tenants`**: Tenant organization boundary (`id`, `name`, `slug`, `currency`, `default_contingency_pct`, `retention_days`, `created_at`).
- **`users`**: System accounts (`id`, `tenant_id`, `email`, `hashed_password`, `full_name`, `role`, `is_active`, `created_at`).
  - Roles: `tenant_admin`, `delivery_manager`, `project_lead`, `contributor`.

### 2. Portfolio & Documents
- **`projects`**: Project delivery container (`id`, `tenant_id`, `name`, `description`, `target_budget`, `target_deadline`, `status`, `created_at`).
- **`documents`**: Uploaded project specifications (`id`, `tenant_id`, `project_id`, `original_filename`, `storage_path`, `file_type`, `file_size_bytes`, `sha256_hash`, `extraction_status`, `total_pages`, `total_words`, `has_text`, `created_at`).

### 3. Asynchronous Jobs & Requirements
- **`background_jobs`**: Observable background execution records (`id`, `tenant_id`, `job_type`, `status`, `progress_pct`, `entity_type`, `entity_id`, `error_message`, `telemetry_json`, `created_at`, `updated_at`).
- **`requirement_drafts`**: Staged AI extraction candidate requirements (`id`, `tenant_id`, `document_id`, `project_id`, `provider_used`, `model_used`, `review_status`, `manager_notes`, `requirements_payload`, `created_at`).
- **`requirement_baselines`**: Immutable approved requirement baselines (`id`, `tenant_id`, `project_id`, `version`, `approved_by`, `manager_notes`, `change_summary`, `requirements_payload`, `approved_at`).

### 4. Planning & WBS
- **`wbs_tasks`**: Work breakdown deliverables (`id`, `tenant_id`, `project_id`, `task_code`, `title`, `description`, `required_role`, `optimistic_hours`, `most_likely_hours`, `pessimistic_hours`, `pert_expected_hours`, `status`, `is_critical_path`, `sort_order`, `created_at`).
- **`task_dependencies`**: Directed edges of the WBS DAG (`id`, `tenant_id`, `project_id`, `predecessor_task_id`, `successor_task_id`, `dependency_type`, `lag_hours`, `created_at`).
  - Constraint: Unique pair `(predecessor_task_id, successor_task_id)` preventing duplicate edges.

### 5. Estimation & Risk
- **`project_estimates`**: Deterministic cost & schedule calculations (`id`, `tenant_id`, `project_id`, `baseline_version`, `total_pert_hours`, `total_labor_cost`, `contingency_pct`, `contingency_cost`, `total_cost`, `currency`, `estimated_duration_days`, `critical_path_tasks_json`, `role_breakdown_json`, `rate_card_version`, `created_at`).
- **`project_risks`**: $L \times I$ Risk Register entries (`id`, `tenant_id`, `project_id`, `risk_code`, `title`, `category`, `description`, `likelihood`, `impact`, `risk_score`, `risk_level`, `supporting_evidence`, `mitigation_strategy`, `risk_owner`, `status`, `created_at`).
- **`feasibility_assessments`**: 7-dimension feasibility audits (`id`, `tenant_id`, `project_id`, `overall_status`, `overall_score`, `dimensions_json`, `limitations_json`, `summary`, `created_at`).

### 6. Workforce Intelligence
- **`workforce_members`**: Talent directory and capacity (`id`, `tenant_id`, `user_id`, `full_name`, `role`, `hourly_rate`, `currency`, `skills_json`, `experience_years`, `availability_pct`, `max_weekly_hours`, `active_projects_count`, `created_at`).
- **`team_recommendations`**: Explainable candidate rankings (`id`, `tenant_id`, `project_id`, `role_needed`, `candidate_id`, `candidate_name`, `match_score`, `skill_score`, `availability_score`, `experience_score`, `workload_score`, `rationale`, `manager_status`, `manager_notes`, `created_at`, `reviewed_at`).

### 7. Execution & Analytics
- **`project_milestones`**: Key delivery milestones (`id`, `tenant_id`, `project_id`, `title`, `description`, `due_date`, `status`, `completed_at`, `created_at`).
- **`task_update_records`**: Auditable progress and logged time (`id`, `tenant_id`, `task_id`, `updated_by_id`, `hours_logged`, `previous_status`, `new_status`, `progress_notes`, `blocker_flag`, `blocker_description`, `created_at`).
- **`historical_project_outcomes`**: Validated completion snapshots for calibration (`id`, `tenant_id`, `project_name`, `category`, `estimated_hours`, `actual_hours`, `effort_variance_pct`, `cost_variance_pct`, `calibration_factor`, `recorded_at`).

### 8. Governance & Reporting
- **`project_reports`**: Archived PDF delivery book snapshots (`id`, `tenant_id`, `project_id`, `title`, `report_type`, `baseline_version`, `storage_path`, `file_size_bytes`, `sha256_hash`, `generated_by`, `created_at`).
- **`audit_logs`**: Immutable security and administrative event ledger (`id`, `tenant_id`, `user_id`, `user_email`, `action`, `entity_type`, `entity_id`, `details_json`, `ip_address`, `created_at`).
- **`correction_requests`**: Employee work record correction requests (`id`, `tenant_id`, `requester_id`, `record_type`, `record_id`, `reason`, `status`, `reviewed_by_id`, `created_at`, `resolved_at`).

---

## Alembic Migration Lineage

- Migration file: `backend/migrations/versions/f36fb43df254_initial_schema.py`
- Head Revision: `f36fb43df254`
- Command to apply migrations:
  ```powershell
  cd backend
  .venv\Scripts\alembic upgrade head
  ```
