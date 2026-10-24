import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from app.core.database import Base


class CorrectionRequest(Base):
    """SQLAlchemy model for contributor metric/work record correction challenges."""

    __tablename__ = "correction_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    user_name = Column(String(255), nullable=False)
    record_type = Column(String(50), nullable=False)  # task_hours, metric, blocker
    record_id = Column(String(36), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="pending")  # pending, approved, rejected
    manager_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
