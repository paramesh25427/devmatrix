import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Text, ForeignKey
from app.core.database import Base


class Project(Base):
    """SQLAlchemy model for delivery projects."""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Statuses: intake, planning, in_progress, completed, on_hold
    status = Column(String(50), nullable=False, default="intake")
    target_budget = Column(Float, nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    target_deadline = Column(String(50), nullable=True)
    active_baseline_version = Column(String(20), nullable=True, default="0")
    created_by_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
