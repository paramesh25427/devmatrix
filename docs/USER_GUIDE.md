# DevMatrix AI — Comprehensive User & Operator Guide

## 1. Quick Start Guide (Windows Development Setup)

### Prerequisites
- Windows 10/11 with PowerShell
- Python 3.11+
- Node.js 18+ & npm
- Git

---

### Step 1: Environment Configuration
Ensure `.env` exists in `backend/` with canonical database and storage paths:

```bash
# In backend/.env
APP_ENV=development
SECRET_KEY=devmatrix-super-secret-jwt-key-2026-production-ready
DATABASE_URL=sqlite:///E:/hackthon/Devmatrix/data/devmatrix.db
STORAGE_DIR=E:/hackthon/Devmatrix/storage

# AI Providers (Leave unset for offline demonstration mode)
GEMINI_API_KEY=
NVIDIA_NIM_API_KEY=
```

---

### Step 2: Apply Database Migrations & Seed Demo Tenant
From the project root:

```powershell
# 1. Run Alembic migrations against canonical database
cd backend
.venv\Scripts\alembic upgrade head

# 2. Seed development demonstration tenant and users
.venv\Scripts\python -m app.cli.seed_demo
```

This creates the default demo users:
- **Delivery Manager**: `manager@devmatrix.local` / `DevMatrix2026!`
- **Tenant Administrator**: `admin@devmatrix.local` / `DevMatrix2026!`
- **Project Lead**: `lead@devmatrix.local` / `DevMatrix2026!`
- **Contributor**: `contributor@devmatrix.local` / `DevMatrix2026!`

---

### Step 3: Start the Backend & Frontend Servers

**Terminal 1 (Backend API):**
```powershell
cd E:\hackthon\Devmatrix\backend
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at `http://localhost:8000/docs`.

**Terminal 2 (Frontend Client):**
```powershell
cd E:\hackthon\Devmatrix\frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 2. End-to-End Delivery Lifecycle Workflow

### Phase 1: Document Intake & AI Extraction (Module 2 & 3)
1. Navigate to **Document Vault** from the sidebar.
2. Drag and drop project specifications (PDF, DOCX, XLSX, CSV, TXT, MD) into the upload zone.
3. The platform validates magic byte signatures, extracts formatted text, and catalogs word/page counts.
4. Click **AI Reqs** on any document.
5. The observable background pipeline executes:
   - Evaluates Google Gemini 2.5 Flash -> NVIDIA NIM -> Offline Fallback Engine.
   - Extracts business objectives, in/out scope, functional requirements, non-functional requirements, constraints, assumptions, and flags document contradictions.
6. Click **Review & Baseline Approval**. As a Delivery Manager, inspect conflicting statements, enter review notes, and click **Approve Baseline (v1)**.

### Phase 2: WBS Planning & Dependency Validation (Module 4)
1. Navigate to **WBS & Planning**.
2. Click **Generate WBS from Baseline**.
3. Candidate epics and tasks are populated with roles and three-point estimates ($O, M, P$).
4. Add predecessor-successor dependencies. The backend performs Kahn's topological sort and DFS cycle checks, immediately detecting and rejecting circular dependencies.

### Phase 3: Effort, Cost & CPM Schedule Estimation (Module 5)
1. Navigate to **Effort & Schedule**.
2. Adjust the contingency buffer slider (e.g., 15%).
3. Click **Recalculate Estimate**.
4. The deterministic engine calculates:
   - PERT expected hours: $(O + 4M + P) / 6$
   - CPM Critical Path sequence (zero-slack critical sequence)
   - Role labor costs based on approved rate cards
   - Base labor cost + contingency buffer = Total Estimated Cost.

### Phase 4: Feasibility & Risk Register (Module 6)
1. Navigate to **Risks & Feasibility**.
2. Click **Run Feasibility Audit**.
3. View scores and status across the 7 dimensions: Schedule, Budget, Skills, Dependencies, Scope, Data Completeness, and Security.
4. Review the $L \times I$ risk register, filtering by category and inspecting owner assignments.

### Phase 5: Workforce Intelligence & Team Allocation (Module 7)
1. Navigate to **Workforce Intelligence**.
2. Click **Generate Recommendations**.
3. View explainable candidate ranking cards with 4-factor scoring breakdown:
   - Skill Fit (40%)
   - Availability (30%)
   - Experience (20%)
   - Current Workload (10%)
4. Review the transparent rationale and click **Approve Assignment**.

### Phase 6: Project Execution & Tracking (Module 8)
1. Navigate to **Execution & Progress**.
2. Contributors select their deliverable task, enter hours worked, select updated status (`in_progress`, `completed`, `blocked`), and enter notes.
3. If an impediment arises, toggle **Flag as active blocker** and describe the issue. Blockers immediately notify managers on the executive dashboard.

### Phase 7: Delivery Analytics & Calibration (Modules 9 & 10)
1. Navigate to **Delivery Analytics**.
2. Inspect effort variance and velocity curves built on legitimate work records.
3. Review the historical learning table. If validated completed projects $N < 5$, a transparent warning notifies that calibration factors remain unadjusted to prevent statistical bias.

### Phase 8: Executive PDF Delivery Book (Module 12)
1. Navigate to **PDF Reports**.
2. Click **Generate Delivery Report**.
3. ReportLab compiles the 15-section project delivery book from stored database records.
4. Click **Download PDF** to inspect or share the formatted document.
