# DevMatrix AI — Architectural Decision Records (ADR)

## ADR-001: Canonical Database Path Resolution
- **Context:** Previously, `database_url: str = "sqlite:///./devmatrix.db"` created two separate SQLite databases depending on whether processes were launched from root `E:\hackthon\Devmatrix` or from `backend/`.
- **Decision:** Resolve the database path deterministically using an absolute path anchored to `DEVMATRIX_DATA_DIR` or `<ROOT>/data/devmatrix.db`.
- **Status:** Accepted & Implemented.

## ADR-002: Test Database Isolation
- **Context:** Automated tests ran against whatever local database file was resolved, risking test pollution or modifying active developer data.
- **Decision:** Configure pytest fixtures with an isolated temporary SQLite database for every test session, overriding the dependency `get_db`.
- **Status:** Accepted & Implemented.

## ADR-003: Asynchronous Observable Extraction Jobs
- **Context:** Requirement extraction held client HTTP requests open for up to 60-120 seconds, risking HTTP client timeouts and UI freezing.
- **Decision:** Introduce a lightweight in-process background job lifecycle (`JobManager`) with statuses `queued`, `running`, `succeeded`, `partially_succeeded`, `failed`, `cancelled`. The API returns an HTTP 202 with `job_id` immediately; the frontend polls the job endpoint with exponential backoff.
- **Status:** Accepted & Implemented.

## ADR-004: Multi-Provider AI Fallback Ordering
- **Context:** Unreliable or rate-limited AI providers must not break the user workflow.
- **Decision:** Primary provider is Google Gemini (`gemini-2.5-flash`), with automated fallback to NVIDIA NIM (`nvidia/nemotron-3.5-lightning-30b-a3b`). Grok is preserved as optional/disabled by default. A deterministic offline mock provider is active when no valid keys are supplied.
- **Status:** Accepted & Implemented.

## ADR-005: Strict Determinism for Business Metrics
- **Context:** LLMs are prone to hallucinating mathematical results and schedule logic.
- **Decision:** All estimation (PERT effort, role costs, CPM schedules), risk indices ($L \times I$), and team candidate ranking are calculated strictly using deterministic Python algorithms. The LLM only proposes raw candidate requirements and task breakdowns.
- **Status:** Accepted & Implemented.

## ADR-006: Rejection of Surveillance-Based Productivity Metrics
- **Context:** Employee tracking systems often monitor keystrokes, mouse clicks, or webcam frames.
- **Decision:** DevMatrix strictly rejects surveillance metrics. Delivery metrics rely exclusively on work artifacts: accepted tasks, milestone deliveries, documented blockers, and verified code/deliverable quality.
- **Status:** Accepted & Implemented.

## ADR-007: PDF Generation via ReportLab
- **Context:** Reports must be professional, downloadable, and generated deterministically from saved database snapshots.
- **Decision:** Use ReportLab to build structured PDF reports containing table of contents, executive summary, approved requirements, WBS, cost/schedule tables, and risk registers.
- **Status:** Accepted & Implemented.
