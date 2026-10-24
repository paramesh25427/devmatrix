import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from app.core.database import Base


class ProjectReport(Base):
    """SQLAlchemy model for downloadable generated project reports."""

    __tablename__ = "project_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    report_type = Column(String(50), nullable=False, default="comprehensive_project_plan")
    baseline_version = Column(Integer, nullable=False, default=1)
    file_path = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    generated_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
