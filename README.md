# devmatrix
System that automates an software managers job

# DevMatrix AI

AI-powered project planning and workforce intelligence platform.

---

## Architecture Overview

```
devmatrix-ai/
├── .gitignore              # Global git ignore definitions
├── README.md               # Quickstart and module documentation
├── backend/                # Python + FastAPI backend service
│   ├── .env.example        # Environment variable template
│   ├── requirements.txt    # Python dependencies
│   ├── pytest.ini          # Pytest configuration
│   ├── storage/            # Dedicated application-managed document storage
│   │   ├── uploads/        # Stored original files with UUID storage keys
│   │   └── extracted/      # Structured JSON extraction payloads
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI application entrypoint & health endpoint
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── documents.py# Module 1 Document intake, listing & deletion API
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py   # Pydantic Settings (upload limits, storage paths)
│   │   │   └── database.py # SQLAlchemy SQLite connection & Base
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── document.py # SQLAlchemy Document metadata entity
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── document.py # Pydantic request/response schemas
│   │   └── services/
│   │       ├── __init__.py
│   │       └── extractor.py# PDF, DOCX, XLSX, CSV, TXT, MD parsing engine
│   └── tests/
│       ├── __init__.py
│       ├── test_health.py  # Health check integration test
│       └── test_documents.py# Module 1 document validation & extraction tests
└── frontend/               # React + TypeScript + Vite + Tailwind CSS
    ├── .env                # Local development environment configuration
    ├── .env.example        # Frontend environment template
    ├── package.json        # NPM dependencies & scripts
    ├── vite.config.ts      # Vite & Vitest configuration
    ├── tsconfig.json       # TypeScript configuration
    ├── tailwind.config.js  # Tailwind CSS configuration
    ├── postcss.config.js   # PostCSS configuration
    ├── index.html          # HTML entry
    └── src/
        ├── App.tsx         # DevMatrix AI Module 1 Dashboard
        ├── App.test.tsx    # Vitest component test
        ├── index.css       # Tailwind stylesheet
        ├── main.tsx        # React DOM render entry
        ├── setupTests.ts   # Testing Library DOM matchers
        ├── components/
        │   ├── DocumentUploadZone.tsx # Drag & Drop intake with client checks
        │   ├── DocumentList.tsx       # Filterable catalog with format badges
        │   ├── DocumentPreviewModal.tsx# Structured section & spreadsheet preview
        │   └── HealthIndicator.tsx    # Live backend & database connectivity pill
        ├── services/
        │   └── api.ts                 # Typed fetch client for backend endpoints
        └── types/
            └── document.ts            # Frontend TypeScript models
```

---

## Module 1: Project Intake & Document Processing

### Supported Formats
- **PDF (`.pdf`)**: Page-by-page text extraction preserving page numbering. Warns if no text is found (OCR unsupported).
- **DOCX (`.docx`)**: Preserves sequential text paragraphs and tabular structures.
- **XLSX (`.xlsx`)**: Extracts multi-sheet workbooks into structured tables without evaluating formulas as executable code.
- **CSV (`.csv`)**: Preserves headers and row/column relationships.
- **TXT & Markdown (`.txt`, `.md`)**: Preserves readable plain and markdown formatted text.

### Module 1 API Endpoints
- `POST /api/documents/upload`: Multipart file upload with magic byte sniffing, size limits, text extraction, and SQLite persistence.
- `GET /api/documents`: Returns list of all cataloged documents with extraction summary statistics.
- `GET /api/documents/{doc_id}`: Retrieves complete document metadata and structured section/spreadsheet extraction.
- `DELETE /api/documents/{doc_id}`: Deletes document record from SQLite and removes associated storage artifacts.
- `GET /api/health`: Verifies API operational status and SQLite database connectivity.

---

## Module 2: AI Requirement Extraction with Multi-Provider Fallback

### Provider Priority Sequence
1. **Primary**: **Google Gemini API** (`gemini-2.5-flash`)
2. **First Fallback**: **xAI Grok API** (Configurable model, default `grok-2-latest`)
3. **Second Fallback**: **NVIDIA NIM** (Configurable model, default `meta/llama-3.1-70b-instruct`)

*Note: OpenAI is explicitly excluded from this architecture.*

### Core Architecture & Design
- **Provider-Independent AI Interface**: `BaseAIAdapter` abstraction with specialized adapters (`GeminiAdapter`, `GrokAdapter`, `NvidiaNimAdapter`).
- **Central Fallback Router**: `AIFallbackRouter` manages sequential provider execution, backoff, and attempt telemetry.
- **Strict Pydantic Validation & Repair**: All providers output to the same `ProjectRequirementsData` schema. If a provider's output fails Pydantic validation, a targeted schema repair attempt is performed before falling back to the next provider.
- **Data Provenance Citations**: Extracted requirements link directly to document sections (`[Page X]`, `[Sheet: Y]`, `[DOCX Section: Z]`). Unsupported or ambiguous statements are flagged with `needs_verification: true` and documented reasons. Missing information is captured as structured clarification questions, never hallucinated as confirmed facts.
- **Manager Review Workflow**: Requirements remain in draft status (`pending_review`) until a manager explicitly approves or requests revisions with feedback notes (`PATCH /api/requirements/{draft_id}/review`). Approval is never automatic.

### Module 2 API Endpoints
- `POST /api/requirements/extract/{doc_id}`: Initiates multi-provider AI requirement extraction from an extracted document.
- `GET /api/requirements/{draft_id}`: Fetches complete requirement draft payload, provenance, and fallback routing trace.
- `GET /api/requirements/document/{doc_id}`: Lists all requirement drafts created for a specific intake document.
- `PATCH /api/requirements/{draft_id}/review`: Records manager review decision (`approved`, `rejected`, `pending_review`) and feedback notes.

### Security, Secrets & Privacy
- **Zero Secrets in Frontend / Git**: API keys (`GEMINI_API_KEY`, `GROK_API_KEY`, `NVIDIA_NIM_API_KEY`) are read strictly from backend environment variables and never logged or exposed.
- **Zero-Key Automated Testing**: The test suite uses high-fidelity mock adapters to verify fallback, rate-limits, validation failures, and repair cycles without external API calls or real keys.
- **Privacy Notice**: Real extraction requests transmit parsed document text to the configured external AI providers. No transmission occurs in mock test mode.

---

## Getting Started

### 1. Prerequisites
- **Node.js**: v18+ (verified on v24.21.0) and **npm** (verified on 11.19.0)
- **Python**: 3.11+ (verified on 3.11.9)

---

### 2. Backend Setup

```powershell
# Navigate to backend
cd backend

# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt

# Run Backend Server
python -m uvicorn app.main:app --reload --port 8000
```
- Health Check: `http://localhost:8000/api/health`
- Interactive API Docs: `http://localhost:8000/docs`

#### Run Backend Tests:
```powershell
python -m pytest tests
```

---

### 3. Frontend Setup

```powershell
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run Frontend Dev Server
npm run dev
```
- Application UI: `http://localhost:5173`

#### Run Frontend Tests:
```powershell
npm run test
```

#### Build Frontend:
```powershell
npm run build
```
