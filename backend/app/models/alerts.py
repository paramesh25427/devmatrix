import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from app.core.database import Base


class ProjectAlert(Base):
    """SQLAlchemy model for actionable project alerts and notifications."""

    __tablename__ = "project_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=True, index=True)
    # Types: blocker, overdue_milestone, cost_overrun, risk_critical, job_failed
    alert_type = Column(String(50), nullable=False)
    # Severity: info, warning, critical
    severity = Column(String(20), nullable=False, default="warning")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
