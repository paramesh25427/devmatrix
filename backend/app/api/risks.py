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
from app.models.baseline import RequirementBaseline
from app.models.risk import ProjectRisk, FeasibilityAssessment
from app.services.risk.feasibility_service import FeasibilityService, calculate_risk_level

router = APIRouter(prefix="/api/risks", tags=["risks"])


class RiskItemResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    risk_code: str
    title: str
    category: str
    description: str
    likelihood: int
    impact: int
    risk_score: int
    risk_level: str
    supporting_evidence: Optional[str] = None
    mitigation_strategy: Optional[str] = None
    risk_owner: Optional[str] = None
    status: str
    source: str = "deterministic"
    created_at: datetime


class FeasibilityOverviewResponse(BaseModel):
    overall_status: str
    overall_score: float
    dimensions: Dict[str, Any]
    limitations: List[str]
    summary: str
    risks: List[RiskItemResponse]


class RiskCreateRequest(BaseModel):
    project_id: str
    risk_code: str
    title: str
    category: str = "technical"
    description: str
    likelihood: int = Field(default=3, ge=1, le=5)
    impact: int = Field(default=3, ge=1, le=5)
    supporting_evidence: Optional[str] = None
    mitigation_strategy: Optional[str] = None
    risk_owner: Optional[str] = None


class RiskUpdateRequest(BaseModel):
    likelihood: Optional[int] = Field(None, ge=1, le=5)
    impact: Optional[int] = Field(None, ge=1, le=5)
    mitigation_strategy: Optional[str] = None
    risk_owner: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(identified|mitigated|accepted|closed)$")


def _format_risk_response(r: ProjectRisk) -> RiskItemResponse:
    ev = r.supporting_evidence or ""
    src = "ai_extracted" if "[AI-Extracted" in ev else "deterministic"
    return RiskItemResponse(
        id=r.id,
        tenant_id=r.tenant_id,
        project_id=r.project_id,
        risk_code=r.risk_code,
        title=r.title,
        category=r.category,
        description=r.description,
        likelihood=r.likelihood,
        impact=r.impact,
        risk_score=r.risk_score,
        risk_level=r.risk_level,
        supporting_evidence=r.supporting_evidence,
        mitigation_strategy=r.mitigation_strategy,
        risk_owner=r.risk_owner,
        status=r.status,
        source=src,
        created_at=r.created_at,
    )


@router.post("/evaluate/{project_id}", response_model=FeasibilityOverviewResponse)
def evaluate_project_feasibility(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluates 7-dimension project feasibility and compiles risk register from baseline."""
    # Enforce tenant-isolated project existence check
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

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
            detail="Cannot evaluate feasibility: No approved requirements baseline found. Please approve a requirements baseline first.",
        )

    assessment, risks = FeasibilityService.evaluate_project_feasibility(
        db=db,
        tenant_id=current_user.tenant_id,
        project_id=project_id,
        baseline=baseline,
    )

    return FeasibilityOverviewResponse(
        overall_status=assessment.overall_status,
        overall_score=assessment.overall_score,
        dimensions=json.loads(assessment.dimensions_json),
        limitations=json.loads(assessment.limitations_json) if assessment.limitations_json else [],
        summary=assessment.summary,
        risks=[_format_risk_response(r) for r in risks],
    )


@router.get("/{project_id}", response_model=FeasibilityOverviewResponse)
def get_project_risks(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves feasibility dimensions and risk items for a project."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    assessment = (
        db.query(FeasibilityAssessment)
        .filter(FeasibilityAssessment.tenant_id == current_user.tenant_id, FeasibilityAssessment.project_id == project_id)
        .first()
    )
    risks = (
        db.query(ProjectRisk)
        .filter(ProjectRisk.tenant_id == current_user.tenant_id, ProjectRisk.project_id == project_id)
        .order_by(ProjectRisk.risk_score.desc())
        .all()
    )

    if not assessment:
        # Check if baseline exists and evaluate
        baseline = (
            db.query(RequirementBaseline)
            .filter(
                RequirementBaseline.tenant_id == current_user.tenant_id,
                RequirementBaseline.project_id == project_id,
                RequirementBaseline.is_active == True,
            )
            .first()
        )
        if baseline:
            assessment, risks = FeasibilityService.evaluate_project_feasibility(
                db=db, tenant_id=current_user.tenant_id, project_id=project_id, baseline=baseline
            )
        else:
            return FeasibilityOverviewResponse(
                overall_status="pending_baseline",
                overall_score=0.0,
                dimensions={},
                limitations=["No requirements baseline approved yet"],
                summary="Please approve a requirements baseline to generate feasibility evaluation.",
                risks=[],
            )

    return FeasibilityOverviewResponse(
        overall_status=assessment.overall_status,
        overall_score=assessment.overall_score,
        dimensions=json.loads(assessment.dimensions_json),
        limitations=json.loads(assessment.limitations_json) if assessment.limitations_json else [],
        summary=assessment.summary,
        risks=[_format_risk_response(r) for r in risks],
    )


@router.put("/item/{risk_id}", response_model=RiskItemResponse)
def update_risk_item(
    risk_id: str,
    payload: RiskUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates risk status, owner, likelihood, impact, or mitigation strategy with manager review."""
    risk = (
        db.query(ProjectRisk)
        .filter(ProjectRisk.id == risk_id, ProjectRisk.tenant_id == current_user.tenant_id)
        .first()
    )
    if not risk:
        raise HTTPException(status_code=404, detail=f"Risk item '{risk_id}' not found.")

    if payload.likelihood is not None:
        risk.likelihood = payload.likelihood
    if payload.impact is not None:
        risk.impact = payload.impact

    score = risk.likelihood * risk.impact
    risk.risk_score = score
    risk.risk_level = calculate_risk_level(score)

    if payload.mitigation_strategy is not None:
        risk.mitigation_strategy = payload.mitigation_strategy
    if payload.risk_owner is not None:
        risk.risk_owner = payload.risk_owner
    if payload.status is not None:
        risk.status = payload.status

    risk.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(risk)

    return _format_risk_response(risk)


@router.post("/item", response_model=RiskItemResponse)
def create_custom_risk_item(
    payload: RiskCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a custom project risk item."""
    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{payload.project_id}' not found.")

    score = payload.likelihood * payload.impact
    level = calculate_risk_level(score)

    risk = ProjectRisk(
        id=str(uuid.uuid4()),
        tenant_id=current_user.tenant_id,
        project_id=payload.project_id,
        risk_code=payload.risk_code,
        title=payload.title,
        category=payload.category,
        description=payload.description,
        likelihood=payload.likelihood,
        impact=payload.impact,
        risk_score=score,
        risk_level=level,
        supporting_evidence=payload.supporting_evidence,
        mitigation_strategy=payload.mitigation_strategy,
        risk_owner=payload.risk_owner or "Project Lead",
        status="identified",
    )
    db.add(risk)
    db.commit()
    db.refresh(risk)

    return _format_risk_response(risk)
