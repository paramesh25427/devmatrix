import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.wbs import WBSTask, TaskDependency
from app.models.baseline import RequirementBaseline
from app.services.planning.wbs_service import WBSService, CyclicDependencyError

router = APIRouter(prefix="/api/wbs", tags=["wbs"])


class TaskItemResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    baseline_version: int
    task_code: str
    title: str
    description: Optional[str]
    epic_name: Optional[str]
    required_role: str
    optimistic_hours: float
    most_likely_hours: float
    pessimistic_hours: float
    expected_hours: float
    variance_hours: float
    assigned_user_id: Optional[str]
    assigned_user_name: Optional[str]
    status: str
    progress_percentage: float = 0.0
    actual_hours: float
    blocker_notes: Optional[str]
    is_critical_path: bool
    source_requirement_ids: List[str]
    order_index: int
    created_at: datetime


class DependencyItemResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: str


class WBSOverviewResponse(BaseModel):
    tasks: List[TaskItemResponse]
    dependencies: List[DependencyItemResponse]
    total_pert_hours: float
    critical_path_task_codes: List[str]
    is_dag_valid: bool
    cycle_error: Optional[str]


class TaskCreateRequest(BaseModel):
    project_id: str
    task_code: str
    title: str
    description: Optional[str] = None
    epic_name: Optional[str] = "General"
    required_role: str = "Full-Stack Engineer"
    optimistic_hours: float = 8.0
    most_likely_hours: float = 16.0
    pessimistic_hours: float = 32.0
    source_requirement_ids: List[str] = []


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    epic_name: Optional[str] = None
    required_role: Optional[str] = None
    optimistic_hours: Optional[float] = None
    most_likely_hours: Optional[float] = None
    pessimistic_hours: Optional[float] = None
    status: Optional[str] = None
    progress_percentage: Optional[float] = None
    actual_hours: Optional[float] = None
    blocker_notes: Optional[str] = None
    assigned_user_id: Optional[str] = None
    assigned_user_name: Optional[str] = None


class DependencyCreateRequest(BaseModel):
    project_id: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: str = "finish_to_start"


@router.post("/generate/{project_id}", response_model=List[TaskItemResponse])
def generate_wbs(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates candidate WBS tasks from the project's approved requirements baseline."""
    baseline = (
        db.query(RequirementBaseline)
        .filter(
            RequirementBaseline.tenant_id == current_user.tenant_id,
            RequirementBaseline.project_id == project_id,
            RequirementBaseline.is_active == True,
        )
        .first()
    )
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate WBS: No approved requirements baseline found. Please approve a requirements baseline first.",
        )

    tasks = WBSService.generate_wbs_from_baseline(
        db=db,
        tenant_id=current_user.tenant_id,
        project_id=project_id,
        baseline=baseline,
    )

    return [
        TaskItemResponse(
            id=t.id,
            tenant_id=t.tenant_id,
            project_id=t.project_id,
            baseline_version=t.baseline_version,
            task_code=t.task_code,
            title=t.title,
            description=t.description,
            epic_name=t.epic_name,
            required_role=t.required_role,
            optimistic_hours=t.optimistic_hours,
            most_likely_hours=t.most_likely_hours,
            pessimistic_hours=t.pessimistic_hours,
            expected_hours=t.expected_hours,
            variance_hours=t.variance_hours,
            assigned_user_id=t.assigned_user_id,
            assigned_user_name=t.assigned_user_name,
            status=t.status,
            progress_percentage=getattr(t, "progress_percentage", 0.0) or 0.0,
            actual_hours=t.actual_hours,
            blocker_notes=t.blocker_notes,
            is_critical_path=t.is_critical_path,
            source_requirement_ids=json.loads(t.source_requirement_ids_json) if t.source_requirement_ids_json else [],
            order_index=t.order_index,
            created_at=t.created_at,
        )
        for t in tasks
    ]


@router.get("/{project_id}", response_model=WBSOverviewResponse)
def get_wbs_overview(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all WBS tasks and dependencies, validating DAG topology."""
    tasks = (
        db.query(WBSTask)
        .filter(WBSTask.tenant_id == current_user.tenant_id, WBSTask.project_id == project_id)
        .order_by(WBSTask.order_index.asc())
        .all()
    )
    dependencies = (
        db.query(TaskDependency)
        .filter(TaskDependency.tenant_id == current_user.tenant_id, TaskDependency.project_id == project_id)
        .all()
    )

    is_valid = True
    cycle_err = None
    try:
        if tasks:
            WBSService.validate_dependencies(tasks, dependencies)
    except CyclicDependencyError as exc:
        is_valid = False
        cycle_err = str(exc)

    total_hours = sum(t.expected_hours for t in tasks)
    critical_codes = [t.task_code for t in tasks if t.is_critical_path]

    return WBSOverviewResponse(
        tasks=[
            TaskItemResponse(
                id=t.id,
                tenant_id=t.tenant_id,
                project_id=t.project_id,
                baseline_version=t.baseline_version,
                task_code=t.task_code,
                title=t.title,
                description=t.description,
                epic_name=t.epic_name,
                required_role=t.required_role,
                optimistic_hours=t.optimistic_hours,
                most_likely_hours=t.most_likely_hours,
                pessimistic_hours=t.pessimistic_hours,
                expected_hours=t.expected_hours,
                variance_hours=t.variance_hours,
                assigned_user_id=t.assigned_user_id,
                assigned_user_name=t.assigned_user_name,
                status=t.status,
                progress_percentage=getattr(t, "progress_percentage", 0.0) or 0.0,
                actual_hours=t.actual_hours,
                blocker_notes=t.blocker_notes,
                is_critical_path=t.is_critical_path,
                source_requirement_ids=json.loads(t.source_requirement_ids_json) if t.source_requirement_ids_json else [],
                order_index=t.order_index,
                created_at=t.created_at,
            )
            for t in tasks
        ],
        dependencies=[
            DependencyItemResponse(
                id=d.id,
                tenant_id=d.tenant_id,
                project_id=d.project_id,
                predecessor_task_id=d.predecessor_task_id,
                successor_task_id=d.successor_task_id,
                dependency_type=d.dependency_type,
            )
            for d in dependencies
        ],
        total_pert_hours=round(total_hours, 2),
        critical_path_task_codes=critical_codes,
        is_dag_valid=is_valid,
        cycle_error=cycle_err,
    )


@router.post("/task", response_model=TaskItemResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a custom task within the WBS."""
    expected, variance = WBSService.calculate_pert(
        payload.optimistic_hours, payload.most_likely_hours, payload.pessimistic_hours
    )
    t_id = str(uuid.uuid4())
    count = db.query(WBSTask).filter(WBSTask.project_id == payload.project_id).count()

    task = WBSTask(
        id=t_id,
        tenant_id=current_user.tenant_id,
        project_id=payload.project_id,
        baseline_version=1,
        task_code=payload.task_code,
        title=payload.title,
        description=payload.description,
        epic_name=payload.epic_name,
        required_role=payload.required_role,
        optimistic_hours=payload.optimistic_hours,
        most_likely_hours=payload.most_likely_hours,
        pessimistic_hours=payload.pessimistic_hours,
        expected_hours=expected,
        variance_hours=variance,
        source_requirement_ids_json=json.dumps(payload.source_requirement_ids),
        order_index=count,
        status="not_started",
        actual_hours=0.0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return TaskItemResponse(
        id=task.id,
        tenant_id=task.tenant_id,
        project_id=task.project_id,
        baseline_version=task.baseline_version,
        task_code=task.task_code,
        title=task.title,
        description=task.description,
        epic_name=task.epic_name,
        required_role=task.required_role,
        optimistic_hours=task.optimistic_hours,
        most_likely_hours=task.most_likely_hours,
        pessimistic_hours=task.pessimistic_hours,
        expected_hours=task.expected_hours,
        variance_hours=task.variance_hours,
        assigned_user_id=task.assigned_user_id,
        assigned_user_name=task.assigned_user_name,
        status=task.status,
        progress_percentage=getattr(task, "progress_percentage", 0.0) or 0.0,
        actual_hours=task.actual_hours,
        blocker_notes=task.blocker_notes,
        is_critical_path=task.is_critical_path,
        source_requirement_ids=payload.source_requirement_ids,
        order_index=task.order_index,
        created_at=task.created_at,
    )


@router.post("/dependency", response_model=DependencyItemResponse, status_code=status.HTTP_201_CREATED)
def add_dependency(
    payload: DependencyCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Adds a task dependency and verifies DAG integrity.
    Rejects cyclic dependencies with HTTP 400.
    """
    tasks = (
        db.query(WBSTask)
        .filter(WBSTask.tenant_id == current_user.tenant_id, WBSTask.project_id == payload.project_id)
        .all()
    )
    existing_deps = (
        db.query(TaskDependency)
        .filter(TaskDependency.tenant_id == current_user.tenant_id, TaskDependency.project_id == payload.project_id)
        .all()
    )

    dep_id = str(uuid.uuid4())
    candidate_dep = TaskDependency(
        id=dep_id,
        tenant_id=current_user.tenant_id,
        project_id=payload.project_id,
        predecessor_task_id=payload.predecessor_task_id,
        successor_task_id=payload.successor_task_id,
        dependency_type=payload.dependency_type,
    )

    # Test adding candidate dependency for cycle detection
    try:
        WBSService.validate_dependencies(tasks, existing_deps + [candidate_dep])
    except CyclicDependencyError as cycle_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(cycle_err),
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )

    db.add(candidate_dep)
    db.commit()
    db.refresh(candidate_dep)

    return DependencyItemResponse(
        id=candidate_dep.id,
        tenant_id=candidate_dep.tenant_id,
        project_id=candidate_dep.project_id,
        predecessor_task_id=candidate_dep.predecessor_task_id,
        successor_task_id=candidate_dep.successor_task_id,
        dependency_type=candidate_dep.dependency_type,
    )
