import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.project import Project
from app.models.wbs import WBSTask
from app.models.execution import ProjectMilestone, TaskUpdateRecord
from app.models.alerts import ProjectAlert
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/execution", tags=["execution"])

VALID_TASK_STATUSES = {"not_started", "in_progress", "blocked", "in_review", "completed"}


class MilestoneResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    title: str
    description: Optional[str]
    due_date: str
    status: str
    completed_at: Optional[datetime]
    created_at: datetime


class TaskUpdateRequestPayload(BaseModel):
    task_id: str
    hours_logged: float = 0.0
    new_status: str
    progress_percentage: Optional[float] = None
    progress_notes: Optional[str] = None
    blocker_flag: bool = False
    blocker_description: Optional[str] = None


class TaskUpdateRecordResponse(BaseModel):
    id: str
    task_id: str
    user_name: str
    hours_logged: float
    previous_status: str
    new_status: str
    progress_percentage: float
    progress_notes: Optional[str] = None
    blocker_flag: str
    blocker_description: Optional[str] = None
    created_at: datetime


class ExecutionSummaryResponse(BaseModel):
    project_id: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    overdue_milestones_count: int = 0
    total_planned_hours: float
    total_actual_hours: float
    completion_percentage: float
    milestones: List[MilestoneResponse]
    active_blockers: List[Dict[str, Any]]
    recent_updates: List[TaskUpdateRecordResponse] = []


@router.get("/summary/{project_id}", response_model=ExecutionSummaryResponse)
def get_execution_summary(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculates delivery velocity, planned vs actual effort, and blocker status with tenant isolation."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied.",
        )

    tasks = (
        db.query(WBSTask)
        .filter(WBSTask.tenant_id == current_user.tenant_id, WBSTask.project_id == project_id)
        .order_by(WBSTask.order_index.asc())
        .all()
    )
    milestones = (
        db.query(ProjectMilestone)
        .filter(ProjectMilestone.tenant_id == current_user.tenant_id, ProjectMilestone.project_id == project_id)
        .order_by(ProjectMilestone.due_date.asc())
        .all()
    )
    recent_records = (
        db.query(TaskUpdateRecord)
        .filter(
            TaskUpdateRecord.tenant_id == current_user.tenant_id,
            TaskUpdateRecord.project_id == project_id,
        )
        .order_by(TaskUpdateRecord.created_at.desc())
        .limit(20)
        .all()
    )

    total_tasks = len(tasks)
    completed = sum(1 for t in tasks if t.status == "completed")
    in_progress = sum(1 for t in tasks if t.status == "in_progress")
    blocked = sum(1 for t in tasks if t.status == "blocked")
    total_planned = sum(t.expected_hours for t in tasks)
    total_actual = sum(t.actual_hours for t in tasks)

    # Project-level completion percentage reflects average task progress
    if total_tasks > 0:
        pct = round(sum((getattr(t, "progress_percentage", 0.0) or 0.0) for t in tasks) / total_tasks, 1)
    else:
        pct = 0.0

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    overdue_count = sum(
        1 for m in milestones
        if m.status != "completed" and m.due_date and m.due_date < today_str
    )

    blockers = [
        {"task_id": t.id, "task_code": t.task_code, "title": t.title, "notes": t.blocker_notes}
        for t in tasks if (t.status == "blocked" or t.blocker_notes)
    ]

    return ExecutionSummaryResponse(
        project_id=project_id,
        total_tasks=total_tasks,
        completed_tasks=completed,
        in_progress_tasks=in_progress,
        blocked_tasks=blocked,
        overdue_milestones_count=overdue_count,
        total_planned_hours=round(total_planned, 1),
        total_actual_hours=round(total_actual, 1),
        completion_percentage=pct,
        milestones=[
            MilestoneResponse(
                id=m.id,
                tenant_id=m.tenant_id,
                project_id=m.project_id,
                title=m.title,
                description=m.description,
                due_date=m.due_date,
                status=m.status,
                completed_at=m.completed_at,
                created_at=m.created_at,
            )
            for m in milestones
        ],
        active_blockers=blockers,
        recent_updates=[
            TaskUpdateRecordResponse(
                id=r.id,
                task_id=r.task_id,
                user_name=r.user_name,
                hours_logged=r.hours_logged,
                previous_status=r.previous_status,
                new_status=r.new_status,
                progress_percentage=getattr(r, "progress_percentage", 0.0) or 0.0,
                progress_notes=r.progress_notes,
                blocker_flag=r.blocker_flag,
                blocker_description=r.blocker_description,
                created_at=r.created_at,
            )
            for r in recent_records
        ],
    )


@router.get("/tasks/{project_id}")
def get_project_execution_tasks(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all project WBS tasks with execution tracking metrics."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied.",
        )
    tasks = (
        db.query(WBSTask)
        .filter(WBSTask.tenant_id == current_user.tenant_id, WBSTask.project_id == project_id)
        .order_by(WBSTask.order_index.asc())
        .all()
    )
    return [
        {
            "id": t.id,
            "task_code": t.task_code,
            "title": t.title,
            "required_role": t.required_role,
            "assigned_user_id": t.assigned_user_id,
            "assigned_user_name": t.assigned_user_name,
            "status": t.status,
            "progress_percentage": getattr(t, "progress_percentage", 0.0) or 0.0,
            "expected_hours": t.expected_hours,
            "actual_hours": t.actual_hours,
            "blocker_notes": t.blocker_notes,
            "is_critical_path": t.is_critical_path,
        }
        for t in tasks
    ]


@router.post("/task-update")
def log_task_update(
    payload: TaskUpdateRequestPayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logs effort spent, updates task status, and tracks progress notes and blockers."""
    # 1. Validation: hours_logged
    if payload.hours_logged < 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hours logged cannot be negative.",
        )
    if payload.hours_logged > 1000.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hours logged exceeds maximum allowable batch limit (1000 hrs).",
        )

    # 2. Validation: new_status
    status_norm = payload.new_status.strip().lower()
    if status_norm not in VALID_TASK_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task status '{payload.new_status}'. Allowed values: {', '.join(sorted(VALID_TASK_STATUSES))}.",
        )

    # 3. Validation: progress_percentage
    if payload.progress_percentage is not None:
        if payload.progress_percentage < 0.0 or payload.progress_percentage > 100.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task progress percentage must be between 0.0 and 100.0.",
            )
        target_progress = round(float(payload.progress_percentage), 1)
    else:
        if status_norm == "completed":
            target_progress = 100.0
        elif status_norm == "not_started":
            target_progress = 0.0
        else:
            target_progress = 0.0

    if status_norm == "completed" and target_progress < 100.0:
        target_progress = 100.0

    # 4. Fetch task and check tenant isolation
    task = (
        db.query(WBSTask)
        .filter(WBSTask.id == payload.task_id, WBSTask.tenant_id == current_user.tenant_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or access denied.")

    # 5. Check project ownership
    project = (
        db.query(Project)
        .filter(Project.id == task.project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or access denied.")

    # 6. Validation: blocker description when blocked
    if status_norm == "blocked" and not (payload.blocker_description and payload.blocker_description.strip()):
        if not task.blocker_notes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A blocker description is required when marking a task as Blocked.",
            )

    # If progress percentage was omitted and task is in progress, preserve existing progress if not not_started
    if payload.progress_percentage is None and status_norm not in ("completed", "not_started"):
        target_progress = getattr(task, "progress_percentage", 0.0) or 0.0

    prev_status = task.status
    task.status = status_norm
    task.progress_percentage = target_progress
    task.actual_hours += round(payload.hours_logged, 2)

    is_blocker = payload.blocker_flag or (status_norm == "blocked")
    if is_blocker:
        desc = (payload.blocker_description and payload.blocker_description.strip()) or task.blocker_notes or "Operational blocker identified."
        task.blocker_notes = desc
        db.add(
            ProjectAlert(
                id=str(uuid.uuid4()),
                tenant_id=current_user.tenant_id,
                project_id=task.project_id,
                alert_type="blocker",
                severity="critical",
                title=f"Blocker Reported on {task.task_code}",
                message=f"{task.title}: {desc}",
                created_at=datetime.utcnow(),
            )
        )
    elif not payload.blocker_flag and status_norm != "blocked":
        task.blocker_notes = None

    task.updated_at = datetime.utcnow()

    # 7. Add audit update record
    rec = TaskUpdateRecord(
        id=str(uuid.uuid4()),
        tenant_id=current_user.tenant_id,
        project_id=task.project_id,
        task_id=task.id,
        user_id=current_user.id,
        user_name=current_user.email,
        hours_logged=payload.hours_logged,
        previous_status=prev_status,
        new_status=task.status,
        progress_percentage=task.progress_percentage,
        progress_notes=payload.progress_notes,
        blocker_flag="true" if is_blocker else "false",
        blocker_description=payload.blocker_description,
        created_at=datetime.utcnow(),
    )
    db.add(rec)

    # 8. Add tenant audit log
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="UPDATE_TASK_PROGRESS",
            entity_type="wbs_task",
            entity_id=task.id,
            details_json=json.dumps({
                "task_code": task.task_code,
                "previous_status": prev_status,
                "new_status": task.status,
                "progress_percentage": task.progress_percentage,
                "hours_logged": payload.hours_logged,
                "actual_hours_total": task.actual_hours,
                "blocker_flag": is_blocker,
            }),
            created_at=datetime.utcnow(),
        )
    )

    db.commit()
    db.refresh(task)

    # Automatic workforce performance evidence collection
    try:
        from app.services.workforce.performance_service import WorkforcePerformanceService
        WorkforcePerformanceService.record_task_outcome_evidence(
            db=db,
            tenant_id=current_user.tenant_id,
            task=task,
            user_id=current_user.id,
            user_email=current_user.email,
        )
    except Exception:
        pass

    return {
        "message": "Task updated successfully",
        "task_id": task.id,
        "task_code": task.task_code,
        "new_status": task.status,
        "progress_percentage": task.progress_percentage,
        "actual_hours": task.actual_hours,
    }
