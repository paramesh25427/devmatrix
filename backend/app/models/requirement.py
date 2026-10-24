import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Float, Boolean, Integer
from app.core.database import Base


class RequirementDraft(Base):
    """SQLAlchemy model for AI-extracted project requirements drafts awaiting manager review."""

    __tablename__ = "requirement_drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, default="tenant-default", index=True)
    project_id = Column(String(36), nullable=True, index=True)
    document_id = Column(String(36), nullable=False)
    document_name = Column(String(255), nullable=False)
    provider_used = Column(String(50), nullable=False)
    model_used = Column(String(100), nullable=False)

    status = Column(String(30), nullable=False, default="draft_ready")  # draft_ready, failed
    review_status = Column(String(30), nullable=False, default="pending_review")  # pending_review, approved, rejected
    manager_notes = Column(Text, nullable=True)

    summary = Column(Text, nullable=True)
    overall_confidence = Column(Float, nullable=False, default=0.0)
    raw_json_path = Column(String(255), nullable=True)
    attempt_history_json = Column(Text, nullable=True)

    # Approved baseline tracking
    version = Column(Integer, nullable=False, default=1)
    is_approved_baseline = Column(Boolean, nullable=False, default=False)
    approved_by_id = Column(String(36), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
