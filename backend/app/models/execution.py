import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey
from app.core.database import Base


class ProjectMilestone(Base):
    """SQLAlchemy model for delivery milestones."""

    __tablename__ = "project_milestones"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(String(30), nullable=False)
    # Status: pending, completed, delayed
    status = Column(String(30), nullable=False, default="pending")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TaskUpdateRecord(Base):
    """SQLAlchemy model for task progress update logs and effort entries."""

    __tablename__ = "task_update_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("wbs_tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), nullable=False)
    user_name = Column(String(255), nullable=False)
    hours_logged = Column(Float, nullable=False, default=0.0)
    previous_status = Column(String(30), nullable=False)
    new_status = Column(String(30), nullable=False)
    progress_percentage = Column(Float, nullable=False, default=0.0)
    progress_notes = Column(Text, nullable=True)
    blocker_flag = Column(String(10), nullable=False, default="false")
    blocker_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
