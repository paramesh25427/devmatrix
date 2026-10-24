import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float
from app.core.database import Base


class HistoricalProjectOutcome(Base):
    """SQLAlchemy model for completed and validated project historical performance."""

    __tablename__ = "historical_project_outcomes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, default="web_application")

    estimated_hours = Column(Float, nullable=False, default=0.0)
    actual_hours = Column(Float, nullable=False, default=0.0)
    estimated_cost = Column(Float, nullable=False, default=0.0)
    actual_cost = Column(Float, nullable=False, default=0.0)
    estimated_duration_days = Column(Float, nullable=False, default=0.0)
    actual_duration_days = Column(Float, nullable=False, default=0.0)

    effort_variance_pct = Column(Float, nullable=False, default=0.0)  # (actual - est) / est * 100
    cost_variance_pct = Column(Float, nullable=False, default=0.0)
    calibration_factor = Column(Float, nullable=False, default=1.0)   # actual_hours / estimated_hours

    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
