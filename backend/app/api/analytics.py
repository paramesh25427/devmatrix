import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.wbs import WBSTask
from app.models.historical import HistoricalProjectOutcome

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class OutcomeRecordRequest(BaseModel):
    project_id: str
    project_name: str
    category: str = "web_application"
    estimated_hours: float
    actual_hours: float
    estimated_cost: float
    actual_cost: float
    estimated_duration_days: float
    actual_duration_days: float


class HistoricalSummaryResponse(BaseModel):
    total_completed_projects: int
    average_effort_variance_pct: float
    average_cost_variance_pct: float
    composite_calibration_factor: float
    has_minimum_sample: bool  # Minimum sample policy: N >= 5
    sample_size_policy_message: str
    projects: List[Dict[str, Any]]


class DeliveryIntelligenceResponse(BaseModel):
    project_id: str
    total_planned_hours: float
    total_actual_hours: float
    effort_variance_pct: float
    completed_tasks_count: int
    open_blockers_count: int
    fair_metrics_policy: str
    surveillance_statement: str


@router.get("/delivery/{project_id}", response_model=DeliveryIntelligenceResponse)
def get_delivery_intelligence(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Computes fair, work-related delivery metrics from verified task outcomes.
    Explicitly enforces zero surveillance: No keystroke, mouse, or webcam metrics.
    """
    tasks = (
        db.query(WBSTask)
        .filter(WBSTask.tenant_id == current_user.tenant_id, WBSTask.project_id == project_id)
        .all()
    )

    planned = sum(t.expected_hours for t in tasks)
    actual = sum(t.actual_hours for t in tasks)
    completed = sum(1 for t in tasks if t.status == "completed")
    blockers = sum(1 for t in tasks if t.status == "blocked")
    variance = round(((actual - planned) / max(planned, 1.0)) * 100.0, 1)

    return DeliveryIntelligenceResponse(
        project_id=project_id,
        total_planned_hours=round(planned, 1),
        total_actual_hours=round(actual, 1),
        effort_variance_pct=variance,
        completed_tasks_count=completed,
        open_blockers_count=blockers,
        fair_metrics_policy="Metrics derived solely from verified task acceptance and milestone deliveries.",
        surveillance_statement="DevMatrix AI strictly rejects keystroke, mouse, webcam, or idle-time surveillance.",
    )


@router.get("/historical", response_model=HistoricalSummaryResponse)
def get_historical_calibration(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyzes historical project outcomes within tenant boundaries.
    Enforces minimum sample size (N >= 5) before applying calibration factors to future estimates.
    """
    outcomes = (
        db.query(HistoricalProjectOutcome)
        .filter(HistoricalProjectOutcome.tenant_id == current_user.tenant_id)
        .order_by(HistoricalProjectOutcome.recorded_at.desc())
        .all()
    )

    n = len(outcomes)
    if n == 0:
        return HistoricalSummaryResponse(
            total_completed_projects=0,
            average_effort_variance_pct=0.0,
            average_cost_variance_pct=0.0,
            composite_calibration_factor=1.0,
            has_minimum_sample=False,
            sample_size_policy_message="Insufficient historical data (0 projects). A minimum of 5 completed projects is required to apply calibration factors.",
            projects=[],
        )

    avg_effort_var = sum(o.effort_variance_pct for o in outcomes) / n
    avg_cost_var = sum(o.cost_variance_pct for o in outcomes) / n
    avg_calib = sum(o.calibration_factor for o in outcomes) / n
    has_min = n >= 5

    msg = (
        f"Calibrated on {n} verified enterprise projects. Historical calibration factor {avg_calib:.2f} is statistically valid."
        if has_min
        else f"Preliminary sample size (N={n}). Statistical calibration policy requires N >= 5 completed projects before auto-adjusting estimates."
    )

    return HistoricalSummaryResponse(
        total_completed_projects=n,
        average_effort_variance_pct=round(avg_effort_var, 1),
        average_cost_variance_pct=round(avg_cost_var, 1),
        composite_calibration_factor=round(avg_calib, 2),
        has_minimum_sample=has_min,
        sample_size_policy_message=msg,
        projects=[
            {
                "id": o.id,
                "project_name": o.project_name,
                "category": o.category,
                "estimated_hours": o.estimated_hours,
                "actual_hours": o.actual_hours,
                "effort_variance_pct": o.effort_variance_pct,
                "cost_variance_pct": o.cost_variance_pct,
                "calibration_factor": o.calibration_factor,
                "recorded_at": o.recorded_at.isoformat(),
            }
            for o in outcomes
        ],
    )


@router.post("/historical/record", status_code=status.HTTP_201_CREATED)
def record_project_outcome(
    payload: OutcomeRecordRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Records a completed and validated project outcome for historical learning."""
    effort_var = ((payload.actual_hours - payload.estimated_hours) / max(payload.estimated_hours, 1.0)) * 100.0
    cost_var = ((payload.actual_cost - payload.estimated_cost) / max(payload.estimated_cost, 1.0)) * 100.0
    calib = payload.actual_hours / max(payload.estimated_hours, 1.0)

    outcome = HistoricalProjectOutcome(
        id=str(uuid.uuid4()),
        tenant_id=current_user.tenant_id,
        project_id=payload.project_id,
        project_name=payload.project_name,
        category=payload.category,
        estimated_hours=payload.estimated_hours,
        actual_hours=payload.actual_hours,
        estimated_cost=payload.estimated_cost,
        actual_cost=payload.actual_cost,
        estimated_duration_days=payload.estimated_duration_days,
        actual_duration_days=payload.actual_duration_days,
        effort_variance_pct=round(effort_var, 1),
        cost_variance_pct=round(cost_var, 1),
        calibration_factor=round(calib, 2),
        recorded_at=datetime.utcnow(),
    )
    db.add(outcome)
    db.commit()
    return {"message": "Historical outcome recorded successfully", "calibration_factor": round(calib, 2)}
