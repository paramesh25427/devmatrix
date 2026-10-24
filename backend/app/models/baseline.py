import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from app.core.database import Base


class RequirementBaseline(Base):
    """SQLAlchemy model for authoritative, manager-approved requirements baselines."""

    __tablename__ = "requirement_baselines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    draft_id = Column(String(36), nullable=False)
    approved_by_id = Column(String(36), nullable=False)
    approved_by_name = Column(String(255), nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    requirements_data_json = Column(Text, nullable=False)  # Full JSON payload of approved requirements
    change_summary = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
