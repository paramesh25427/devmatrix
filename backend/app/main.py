from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import Base, engine, verify_db_connection
import app.models  # Ensures all SQLAlchemy models are registered

# Import API Routers
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.documents import router as documents_router
from app.api.jobs import router as jobs_router
from app.api.requirements import router as requirements_router
from app.api.wbs import router as wbs_router
from app.api.estimation import router as estimation_router
from app.api.risks import router as risks_router
from app.api.workforce import router as workforce_router
from app.api.execution import router as execution_router
from app.api.analytics import router as analytics_router
from app.api.reports import router as reports_router
from app.api.admin import router as admin_router
from app.api.corrections import router as corrections_router


class HealthResponse(BaseModel):
    status: str
    app: str
    database: str
    version: str


# Automatically create database tables for registered SQLAlchemy models
Base.metadata.create_all(bind=engine)

def _ensure_execution_schema():
    """Idempotently adds missing execution tracking columns to existing SQLite tables."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            cursor = conn.execute(text("PRAGMA table_info(wbs_tasks)"))
            cols = [row[1] for row in cursor.fetchall()]
            if cols and "progress_percentage" not in cols:
                conn.execute(text("ALTER TABLE wbs_tasks ADD COLUMN progress_percentage FLOAT NOT NULL DEFAULT 0.0"))
                conn.commit()

            cursor = conn.execute(text("PRAGMA table_info(task_update_records)"))
            cols = [row[1] for row in cursor.fetchall()]
            if cols and "progress_percentage" not in cols:
                conn.execute(text("ALTER TABLE task_update_records ADD COLUMN progress_percentage FLOAT NOT NULL DEFAULT 0.0"))
                conn.commit()
    except Exception:
        pass

_ensure_execution_schema()


def _ensure_workforce_schema():
    """Idempotently adds missing workforce v2 columns to existing SQLite tables."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # 1. Team recommendations alternatives and performance
            cursor = conn.execute(text("PRAGMA table_info(team_recommendations)"))
            rec_cols = [row[1] for row in cursor.fetchall()]
            if rec_cols and "alternatives_json" not in rec_cols:
                conn.execute(text("ALTER TABLE team_recommendations ADD COLUMN alternatives_json TEXT NULL"))
                conn.commit()
            if rec_cols and "performance_score" not in rec_cols:
                conn.execute(text("ALTER TABLE team_recommendations ADD COLUMN performance_score FLOAT NULL"))
                conn.commit()

            # 2. Workforce members onboarding & performance columns
            cursor = conn.execute(text("PRAGMA table_info(workforce_members)"))
            wf_cols = [row[1] for row in cursor.fetchall()]
            if wf_cols:
                if "skill_proficiencies_json" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN skill_proficiencies_json TEXT NULL"))
                if "initial_assessed_score" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN initial_assessed_score FLOAT NULL"))
                if "performance_score" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN performance_score FLOAT NULL"))
                if "has_sufficient_evidence" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN has_sufficient_evidence BOOLEAN NOT NULL DEFAULT 0"))
                if "performance_score_version" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN performance_score_version INTEGER NOT NULL DEFAULT 0"))
                if "is_active" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
                if "is_synthetic" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN is_synthetic BOOLEAN NOT NULL DEFAULT 0"))
                if "created_by_user_id" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN created_by_user_id VARCHAR(36) NULL"))
                if "created_by_user_email" not in wf_cols:
                    conn.execute(text("ALTER TABLE workforce_members ADD COLUMN created_by_user_email VARCHAR(255) NULL"))
                conn.commit()

        # Ensure new tables are created
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass


_ensure_workforce_schema()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="DevMatrix AI — AI-Assisted Project Delivery, Workforce Intelligence & Verification Platform",
)

# CORS configuration restricted to configured frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all 14 domain routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(jobs_router)
app.include_router(requirements_router)
app.include_router(wbs_router)
app.include_router(estimation_router)
app.include_router(risks_router)
app.include_router(workforce_router)
app.include_router(execution_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(corrections_router)


@app.get("/api/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def get_health() -> HealthResponse:
    """Readiness and liveness health check verifying app and database connectivity."""
    db_connected = False
    try:
        db_connected = verify_db_connection()
    except Exception:
        db_connected = False

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        app="DevMatrix AI",
        database="connected" if db_connected else "disconnected",
        version="1.0.0",
    )
