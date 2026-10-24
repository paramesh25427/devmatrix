import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.core.database import Base


class BackgroundJob(Base):
    """SQLAlchemy model for asynchronous background job execution and observable lifecycle."""

    __tablename__ = "background_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=True, index=True)
    document_id = Column(String(36), nullable=True, index=True)
    # job_type: requirement_extraction, wbs_generation, estimation, report_generation
    job_type = Column(String(50), nullable=False)
    # status: queued, running, succeeded, partially_succeeded, failed, cancelled
    status = Column(String(30), nullable=False, default="queued", index=True)
    progress_pct = Column(Integer, nullable=False, default=0)
    message = Column(String(255), nullable=True)
    result_json = Column(Text, nullable=True)
    error_json = Column(Text, nullable=True)
    attempts_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
