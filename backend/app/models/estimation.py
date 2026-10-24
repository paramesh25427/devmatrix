import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Float
from app.core.database import Base


class ProjectEstimate(Base):
    """SQLAlchemy model for calculated project effort, cost, and schedule estimates."""

    __tablename__ = "project_estimates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    baseline_version = Column(Integer, nullable=False, default=1)

    total_pert_hours = Column(Float, nullable=False, default=0.0)
    total_labor_cost = Column(Float, nullable=False, default=0.0)
    contingency_pct = Column(Float, nullable=False, default=15.0)
    contingency_cost = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="USD")

    estimated_duration_days = Column(Float, nullable=False, default=0.0)
    start_date = Column(String(30), nullable=True)
    target_completion_date = Column(String(30), nullable=True)

    critical_path_tasks_json = Column(Text, nullable=True)
    role_breakdown_json = Column(Text, nullable=True)
    rate_card_version = Column(String(50), nullable=False, default="Default Enterprise 2026")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
