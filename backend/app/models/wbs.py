import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Boolean, ForeignKey
from app.core.database import Base


class WBSTask(Base):
    """SQLAlchemy model for Work Breakdown Structure (WBS) tasks."""

    __tablename__ = "wbs_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    baseline_version = Column(Integer, nullable=False, default=1)
    task_code = Column(String(50), nullable=False)  # e.g. TSK-1.1
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    epic_name = Column(String(100), nullable=True)
    parent_task_id = Column(String(36), nullable=True)
    required_role = Column(String(100), nullable=False, default="Full-Stack Engineer")

    # PERT Three-Point Effort Estimation (Hours)
    optimistic_hours = Column(Float, nullable=False, default=8.0)
    most_likely_hours = Column(Float, nullable=False, default=16.0)
    pessimistic_hours = Column(Float, nullable=False, default=32.0)
    expected_hours = Column(Float, nullable=False, default=17.33)  # (O + 4M + P) / 6
    variance_hours = Column(Float, nullable=False, default=16.0)   # ((P - O) / 6) ^ 2

    assigned_user_id = Column(String(36), nullable=True)
    assigned_user_name = Column(String(255), nullable=True)
    
    # Status: not_started, in_progress, blocked, in_review, completed
    status = Column(String(30), nullable=False, default="not_started", index=True)
    progress_percentage = Column(Float, nullable=False, default=0.0)
    actual_hours = Column(Float, nullable=False, default=0.0)
    blocker_notes = Column(Text, nullable=True)
    is_critical_path = Column(Boolean, nullable=False, default=False)

    source_requirement_ids_json = Column(Text, nullable=True)  # Traceability to approved requirements
    order_index = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TaskDependency(Base):
    """SQLAlchemy model for directed task dependency graph."""

    __tablename__ = "task_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    predecessor_task_id = Column(String(36), ForeignKey("wbs_tasks.id", ondelete="CASCADE"), nullable=False)
    successor_task_id = Column(String(36), ForeignKey("wbs_tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String(20), nullable=False, default="finish_to_start")
