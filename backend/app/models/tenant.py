import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.core.database import Base


class Tenant(Base):
    """SQLAlchemy model for enterprise tenants in DevMatrix AI."""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    currency = Column(String(10), nullable=False, default="USD")
    default_contingency_pct = Column(String(20), nullable=False, default="15.0")
    retention_days = Column(String(20), nullable=False, default="365")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
