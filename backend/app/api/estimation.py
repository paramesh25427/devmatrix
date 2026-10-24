import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.estimation import ProjectEstimate
from app.models.wbs import WBSTask
from app.services.estimation.engine import EstimationEngine
from app.services.planning.wbs_service import CyclicDependencyError

router = APIRouter(prefix="/api/estimation", tags=["estimation"])


def _format_critical_path_codes(db: Session, project_id: str, raw_json: Optional[str]) -> List[str]:
    """Ensures serialized critical path items are human-readable task codes (e.g. TSK-1.1)."""
    if not raw_json:
        return []
    try:
        items = json.loads(raw_json)
    except Exception:
        return []
    if not items or not isinstance(items, list):
        return []
    # If stored items are UUIDs (legacy data), map to task_code from database
    sample = str(items[0])
    if len(sample) == 36 and "-" in sample and not sample.startswith("TSK"):
        tasks = db.query(WBSTask.id, WBSTask.task_code).filter(WBSTask.project_id == project_id).all()
        id_to_code = {t[0]: t[1] for t in tasks}
        return [id_to_code.get(item, item) for item in items]
    return [str(x) for x in items]


class EstimateCalculateRequest(BaseModel):
    contingency_pct: float = Field(
        default=15.0,
        ge=0.0,
        le=100.0,
        description="Contingency percentage must be between 0.0 and 100.0 inclusive.",
    )


class EstimateDetailResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    baseline_version: int
    total_pert_hours: float
    total_labor_cost: float
    contingency_pct: float
    contingency_cost: float
    total_cost: float
    currency: str
    estimated_duration_days: float
    critical_path_tasks: List[str]
    role_breakdown: Dict[str, Any]
    rate_card_version: str
    created_at: datetime


@router.post("/calculate/{project_id}", response_model=EstimateDetailResponse)
def calculate_project_estimate(
    project_id: str,
    payload: EstimateCalculateRequest = EstimateCalculateRequest(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes deterministic calculations:
    1. Aggregates PERT expected hours: (O + 4M + P)/6
    2. Maps role hours to approved enterprise rate card
    3. Adds contingency percentage
    4. Computes CPM Critical Path and project duration in working days
    """
    try:
        estimate = EstimationEngine.calculate_project_estimates(
            db=db,
            tenant_id=current_user.tenant_id,
            project_id=project_id,
            contingency_pct=payload.contingency_pct,
        )
    except (ValueError, CyclicDependencyError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )

    return EstimateDetailResponse(
        id=estimate.id,
        tenant_id=estimate.tenant_id,
        project_id=estimate.project_id,
        baseline_version=estimate.baseline_version,
        total_pert_hours=estimate.total_pert_hours,
        total_labor_cost=estimate.total_labor_cost,
        contingency_pct=estimate.contingency_pct,
        contingency_cost=estimate.contingency_cost,
        total_cost=estimate.total_cost,
        currency=estimate.currency,
        estimated_duration_days=estimate.estimated_duration_days,
        critical_path_tasks=_format_critical_path_codes(db, estimate.project_id, estimate.critical_path_tasks_json),
        role_breakdown=json.loads(estimate.role_breakdown_json) if estimate.role_breakdown_json else {},
        rate_card_version=estimate.rate_card_version,
        created_at=estimate.created_at,
    )


@router.get("/{project_id}", response_model=EstimateDetailResponse)
def get_project_estimate(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves the latest calculated project estimate."""
    estimate = (
        db.query(ProjectEstimate)
        .filter(ProjectEstimate.tenant_id == current_user.tenant_id, ProjectEstimate.project_id == project_id)
        .first()
    )
    if not estimate:
        # Calculate automatically if tasks exist
        try:
            estimate = EstimationEngine.calculate_project_estimates(
                db=db,
                tenant_id=current_user.tenant_id,
                project_id=project_id,
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No estimate found for project '{project_id}'. Generate WBS tasks first.",
            )

    return EstimateDetailResponse(
        id=estimate.id,
        tenant_id=estimate.tenant_id,
        project_id=estimate.project_id,
        baseline_version=estimate.baseline_version,
        total_pert_hours=estimate.total_pert_hours,
        total_labor_cost=estimate.total_labor_cost,
        contingency_pct=estimate.contingency_pct,
        contingency_cost=estimate.contingency_cost,
        total_cost=estimate.total_cost,
        currency=estimate.currency,
        estimated_duration_days=estimate.estimated_duration_days,
        critical_path_tasks=_format_critical_path_codes(db, estimate.project_id, estimate.critical_path_tasks_json),
        role_breakdown=json.loads(estimate.role_breakdown_json) if estimate.role_breakdown_json else {},
        rate_card_version=estimate.rate_card_version,
        created_at=estimate.created_at,
    )
