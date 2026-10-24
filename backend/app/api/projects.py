import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.project import Project
from app.models.document import Document
from app.models.baseline import RequirementBaseline
from app.models.wbs import WBSTask
from app.models.estimation import ProjectEstimate

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    target_budget: Optional[float] = None
    currency: str = "USD"
    target_deadline: Optional[str] = None


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    target_budget: Optional[float] = None
    target_deadline: Optional[str] = None


class ProjectSummaryResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    status: str
    target_budget: Optional[float]
    currency: str
    target_deadline: Optional[str]
    active_baseline_version: Optional[str]
    document_count: int
    task_count: int
    total_pert_hours: float
    total_cost: float
    created_at: datetime


@router.get("", response_model=List[ProjectSummaryResponse])
def list_projects(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all delivery projects within the user's isolated tenant scope."""
    projects = (
        db.query(Project)
        .filter(Project.tenant_id == current_user.tenant_id)
        .order_by(Project.created_at.desc())
        .all()
    )

    result = []
    for p in projects:
        doc_count = db.query(Document).filter(Document.project_id == p.id).count()
        task_count = db.query(WBSTask).filter(WBSTask.project_id == p.id).count()
        est = db.query(ProjectEstimate).filter(ProjectEstimate.project_id == p.id).first()

        result.append(
            ProjectSummaryResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                name=p.name,
                description=p.description,
                status=p.status,
                target_budget=p.target_budget,
                currency=p.currency,
                target_deadline=p.target_deadline,
                active_baseline_version=p.active_baseline_version or "0",
                document_count=doc_count,
                task_count=task_count,
                total_pert_hours=est.total_pert_hours if est else 0.0,
                total_cost=est.total_cost if est else 0.0,
                created_at=p.created_at,
            )
        )
    return result


@router.post("", response_model=ProjectSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    request: ProjectCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new project within the current tenant."""
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        tenant_id=current_user.tenant_id,
        name=request.name,
        description=request.description,
        status="intake",
        target_budget=request.target_budget,
        currency=request.currency,
        target_deadline=request.target_deadline,
        active_baseline_version="0",
        created_by_id=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectSummaryResponse(
        id=project.id,
        tenant_id=project.tenant_id,
        name=project.name,
        description=project.description,
        status=project.status,
        target_budget=project.target_budget,
        currency=project.currency,
        target_deadline=project.target_deadline,
        active_baseline_version="0",
        document_count=0,
        task_count=0,
        total_pert_hours=0.0,
        total_cost=0.0,
        created_at=project.created_at,
    )


@router.get("/{project_id}", response_model=ProjectSummaryResponse)
def get_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves project details scoped by tenant."""
    p = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail=f"Project with ID '{project_id}' not found.")

    doc_count = db.query(Document).filter(Document.project_id == p.id).count()
    task_count = db.query(WBSTask).filter(WBSTask.project_id == p.id).count()
    est = db.query(ProjectEstimate).filter(ProjectEstimate.project_id == p.id).first()

    return ProjectSummaryResponse(
        id=p.id,
        tenant_id=p.tenant_id,
        name=p.name,
        description=p.description,
        status=p.status,
        target_budget=p.target_budget,
        currency=p.currency,
        target_deadline=p.target_deadline,
        active_baseline_version=p.active_baseline_version or "0",
        document_count=doc_count,
        task_count=task_count,
        total_pert_hours=est.total_pert_hours if est else 0.0,
        total_cost=est.total_cost if est else 0.0,
        created_at=p.created_at,
    )
