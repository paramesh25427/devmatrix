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
from app.models.workforce import (
    WorkforceMember,
    TeamRecommendation,
    MemberPerformanceEvidence,
    MemberPerformanceScoreHistory,
)
from app.models.audit import AuditLog
from app.services.workforce.recommendation_service import WorkforceRecommendationService
from app.services.workforce.performance_service import WorkforcePerformanceService

router = APIRouter(prefix="/api/workforce", tags=["workforce"])


def _require_delivery_manager(current_user: AuthenticatedUser):
    """Enforces manager authorization for workforce member onboarding, editing, and score corrections."""
    if current_user.role not in ("delivery_manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorized delivery manager role required for workforce onboarding and management.",
        )


class WorkforceMemberResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str] = None
    full_name: str
    role: str
    hourly_rate: float
    currency: str
    skills: List[str]
    skill_proficiencies: Dict[str, str] = {}
    experience_years: float
    availability_pct: float
    max_weekly_hours: float
    active_projects_count: int
    initial_assessed_score: Optional[float] = None
    performance_score: Optional[float] = None
    has_sufficient_evidence: bool = False
    performance_status_label: str = "Insufficient performance history"
    performance_score_version: int = 0
    is_active: bool = True
    is_synthetic: bool = False
    created_by_user_id: Optional[str] = None
    created_by_user_email: Optional[str] = None
    created_at: datetime


class WorkforceCreateRequest(BaseModel):
    full_name: str
    role: str
    hourly_rate: float = Field(default=100.0, gt=0)
    currency: str = "USD"
    skills: List[str] = []
    skill_proficiencies: Optional[Dict[str, str]] = None
    experience_years: float = Field(default=4.0, ge=0)
    availability_pct: float = Field(default=100.0, ge=0, le=100)
    max_weekly_hours: float = Field(default=40.0, ge=0)
    initial_assessed_score: Optional[float] = Field(default=None, ge=0, le=100)


class WorkforceUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    hourly_rate: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = None
    skills: Optional[List[str]] = None
    skill_proficiencies: Optional[Dict[str, str]] = None
    experience_years: Optional[float] = Field(default=None, ge=0)
    availability_pct: Optional[float] = Field(default=None, ge=0, le=100)
    max_weekly_hours: Optional[float] = Field(default=None, ge=0)
    initial_assessed_score: Optional[float] = Field(default=None, ge=0, le=100)


class ScoreCorrectionRequest(BaseModel):
    corrected_score: float = Field(..., ge=0, le=100)
    reason: str = Field(..., min_length=3)


class PerformanceEvidenceResponse(BaseModel):
    id: str
    tenant_id: str
    member_id: str
    project_id: str
    task_id: Optional[str] = None
    event_fingerprint: str
    event_type: str
    planned_hours: float
    actual_hours: float
    effort_variance_ratio: float
    on_schedule: bool
    was_blocked_externally: bool
    quality_outcome: Optional[str] = None
    evidence_notes: Optional[str] = None
    created_at: datetime


class ScoreHistoryResponse(BaseModel):
    id: str
    tenant_id: str
    member_id: str
    score_version: int
    performance_score: Optional[float] = None
    has_sufficient_evidence: bool
    delivery_score: Optional[float] = None
    quality_score: Optional[float] = None
    formula_version: str
    evidence_count: int
    notes: Optional[str] = None
    is_manual_correction: bool
    correction_reason: Optional[str] = None
    corrected_by_user_email: Optional[str] = None
    created_at: datetime


class RecommendationResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    task_id: Optional[str] = None
    task_code: Optional[str] = None
    task_title: Optional[str] = None
    role_needed: str
    candidate_id: str
    candidate_name: str
    match_score: float
    skill_score: float
    availability_score: float
    experience_score: float
    workload_score: float
    performance_score: Optional[float] = None
    rationale: str
    is_synthetic: bool = False
    manager_status: str
    manager_notes: Optional[str] = None
    alternatives: List[Dict[str, Any]] = []
    created_at: datetime
    reviewed_at: Optional[datetime] = None


class OverrideRequest(BaseModel):
    candidate_id: str
    candidate_name: str
    manager_notes: str


class AlternativeSelectRequest(BaseModel):
    candidate_id: str
    manager_notes: Optional[str] = None


class RejectRequest(BaseModel):
    manager_notes: Optional[str] = None


def _format_member_response(m: WorkforceMember) -> WorkforceMemberResponse:
    skills = json.loads(m.skills_json) if m.skills_json else []
    proficiencies = {}
    if getattr(m, "skill_proficiencies_json", None):
        try:
            proficiencies = json.loads(m.skill_proficiencies_json)
        except Exception:
            proficiencies = {}

    perf_score = getattr(m, "performance_score", None)
    has_evidence = bool(getattr(m, "has_sufficient_evidence", False) and perf_score is not None)
    status_label = f"{perf_score:.1f}% Verified" if has_evidence else "Insufficient performance history"

    return WorkforceMemberResponse(
        id=m.id,
        tenant_id=m.tenant_id,
        user_id=m.user_id,
        full_name=m.full_name,
        role=m.role,
        hourly_rate=m.hourly_rate,
        currency=m.currency,
        skills=skills,
        skill_proficiencies=proficiencies,
        experience_years=m.experience_years,
        availability_pct=m.availability_pct,
        max_weekly_hours=m.max_weekly_hours,
        active_projects_count=m.active_projects_count,
        initial_assessed_score=getattr(m, "initial_assessed_score", None),
        performance_score=perf_score,
        has_sufficient_evidence=has_evidence,
        performance_status_label=status_label,
        performance_score_version=getattr(m, "performance_score_version", 0) or 0,
        is_active=getattr(m, "is_active", True) if getattr(m, "is_active", True) is not None else True,
        is_synthetic=bool(getattr(m, "is_synthetic", False) or m.id.startswith("syn-") or "[Synthetic" in m.full_name),
        created_by_user_id=getattr(m, "created_by_user_id", None),
        created_by_user_email=getattr(m, "created_by_user_email", None),
        created_at=m.created_at,
    )


def _format_rec_response(db: Session, r: TeamRecommendation) -> RecommendationResponse:
    task_code = None
    task_title = None
    if r.task_id:
        task = db.query(WBSTask).filter(WBSTask.id == r.task_id).first()
        if task:
            task_code = task.task_code
            task_title = task.title

    is_syn = r.candidate_id.startswith("syn-") or "[Synthetic" in r.candidate_name

    alternatives = []
    if getattr(r, "alternatives_json", None):
        try:
            alternatives = json.loads(r.alternatives_json)
        except Exception:
            alternatives = []

    if not alternatives and not is_syn:
        members = db.query(WorkforceMember).filter(WorkforceMember.tenant_id == r.tenant_id).all()
        if members:
            ranked = WorkforceRecommendationService._rank_candidates_for_role(
                members=members,
                role=r.role_needed,
                task_title=task_title,
            )
            alt_candidates = [c for c in ranked if c[0].id != r.candidate_id][:3]
            for alt_m, alt_scores, alt_rat in alt_candidates:
                alternatives.append({
                    "candidate_id": alt_m.id,
                    "candidate_name": alt_m.full_name,
                    "role": alt_m.role,
                    "hourly_rate": alt_m.hourly_rate,
                    "match_score": alt_scores.get("match_score", 70.0),
                    "skill_score": alt_scores.get("skill_score", 70.0),
                    "availability_score": alt_scores.get("availability_score", 70.0),
                    "experience_score": alt_scores.get("experience_score", 70.0),
                    "workload_score": alt_scores.get("workload_score", 70.0),
                    "performance_score": alt_scores.get("performance_score"),
                    "rationale": alt_rat,
                })
            if alternatives:
                try:
                    r.alternatives_json = json.dumps(alternatives)
                    db.commit()
                except Exception:
                    pass

    return RecommendationResponse(
        id=r.id,
        tenant_id=r.tenant_id,
        project_id=r.project_id,
        task_id=r.task_id,
        task_code=task_code,
        task_title=task_title,
        role_needed=r.role_needed,
        candidate_id=r.candidate_id,
        candidate_name=r.candidate_name,
        match_score=r.match_score,
        skill_score=r.skill_score,
        availability_score=r.availability_score,
        experience_score=r.experience_score,
        workload_score=r.workload_score,
        performance_score=getattr(r, "performance_score", None),
        rationale=r.rationale,
        is_synthetic=is_syn,
        manager_status=r.manager_status,
        manager_notes=r.manager_notes,
        alternatives=alternatives,
        created_at=r.created_at,
        reviewed_at=r.reviewed_at,
    )


@router.get("", response_model=List[WorkforceMemberResponse])
def list_workforce_members(
    include_inactive: bool = False,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists workforce talent profiles in the user's tenant directory."""
    query = db.query(WorkforceMember).filter(WorkforceMember.tenant_id == current_user.tenant_id)
    if not include_inactive:
        query = query.filter(WorkforceMember.is_active != False)
    members = query.order_by(WorkforceMember.full_name.asc()).all()
    return [_format_member_response(m) for m in members]


@router.post("", response_model=WorkforceMemberResponse, status_code=status.HTTP_201_CREATED)
def create_workforce_member(
    payload: WorkforceCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manager-only onboarding for persistent team-member talent profiles."""
    _require_delivery_manager(current_user)

    m_id = str(uuid.uuid4())
    proficiencies_json = json.dumps(payload.skill_proficiencies or {})
    member = WorkforceMember(
        id=m_id,
        tenant_id=current_user.tenant_id,
        full_name=payload.full_name,
        role=payload.role,
        hourly_rate=payload.hourly_rate,
        currency=payload.currency,
        skills_json=json.dumps(payload.skills),
        skill_proficiencies_json=proficiencies_json,
        experience_years=payload.experience_years,
        availability_pct=payload.availability_pct,
        max_weekly_hours=payload.max_weekly_hours,
        active_projects_count=0,
        initial_assessed_score=payload.initial_assessed_score,
        performance_score=None,
        has_sufficient_evidence=False,
        performance_score_version=0,
        is_active=True,
        is_synthetic=False,
        created_by_user_id=current_user.id,
        created_by_user_email=current_user.email,
    )
    db.add(member)
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="WORKFORCE_MEMBER_CREATED",
            entity_type="workforce_member",
            entity_id=m_id,
            details_json=json.dumps({
                "full_name": payload.full_name,
                "role": payload.role,
                "hourly_rate": payload.hourly_rate,
                "experience_years": payload.experience_years,
                "availability_pct": payload.availability_pct,
                "initial_assessed_score": payload.initial_assessed_score,
                "skills": payload.skills,
                "skill_proficiencies": payload.skill_proficiencies,
                "created_by": current_user.email,
            }),
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    db.refresh(member)

    return _format_member_response(member)


@router.get("/members/{member_id}", response_model=WorkforceMemberResponse)
def get_workforce_member(
    member_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves a single workforce member profile with tenant isolation."""
    member = (
        db.query(WorkforceMember)
        .filter(WorkforceMember.id == member_id, WorkforceMember.tenant_id == current_user.tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workforce member not found.")
    return _format_member_response(member)


@router.put("/members/{member_id}", response_model=WorkforceMemberResponse)
def update_workforce_member(
    member_id: str,
    payload: WorkforceUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manager-only profile editing for persistent workforce members."""
    _require_delivery_manager(current_user)

    member = (
        db.query(WorkforceMember)
        .filter(WorkforceMember.id == member_id, WorkforceMember.tenant_id == current_user.tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workforce member not found.")

    changes = {}
    if payload.full_name is not None:
        changes["full_name"] = payload.full_name
        member.full_name = payload.full_name
    if payload.role is not None:
        changes["role"] = payload.role
        member.role = payload.role
    if payload.hourly_rate is not None:
        changes["hourly_rate"] = payload.hourly_rate
        member.hourly_rate = payload.hourly_rate
    if payload.currency is not None:
        member.currency = payload.currency
    if payload.skills is not None:
        changes["skills"] = payload.skills
        member.skills_json = json.dumps(payload.skills)
    if payload.skill_proficiencies is not None:
        changes["skill_proficiencies"] = payload.skill_proficiencies
        member.skill_proficiencies_json = json.dumps(payload.skill_proficiencies)
    if payload.experience_years is not None:
        changes["experience_years"] = payload.experience_years
        member.experience_years = payload.experience_years
    if payload.availability_pct is not None:
        changes["availability_pct"] = payload.availability_pct
        member.availability_pct = payload.availability_pct
    if payload.max_weekly_hours is not None:
        changes["max_weekly_hours"] = payload.max_weekly_hours
        member.max_weekly_hours = payload.max_weekly_hours
    if payload.initial_assessed_score is not None:
        changes["initial_assessed_score"] = payload.initial_assessed_score
        member.initial_assessed_score = payload.initial_assessed_score

    member.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="WORKFORCE_MEMBER_UPDATED",
            entity_type="workforce_member",
            entity_id=member.id,
            details_json=json.dumps(changes),
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    db.refresh(member)

    return _format_member_response(member)


@router.post("/members/{member_id}/activate", response_model=WorkforceMemberResponse)
def activate_workforce_member(
    member_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manager-only activation of a workforce member profile."""
    _require_delivery_manager(current_user)

    member = (
        db.query(WorkforceMember)
        .filter(WorkforceMember.id == member_id, WorkforceMember.tenant_id == current_user.tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workforce member not found.")

    member.is_active = True
    member.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="WORKFORCE_MEMBER_ACTIVATED",
            entity_type="workforce_member",
            entity_id=member.id,
            details_json=json.dumps({"full_name": member.full_name}),
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    db.refresh(member)

    return _format_member_response(member)


@router.post("/members/{member_id}/deactivate", response_model=WorkforceMemberResponse)
def deactivate_workforce_member(
    member_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manager-only deactivation of a workforce member profile."""
    _require_delivery_manager(current_user)

    member = (
        db.query(WorkforceMember)
        .filter(WorkforceMember.id == member_id, WorkforceMember.tenant_id == current_user.tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workforce member not found.")

    member.is_active = False
    member.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="WORKFORCE_MEMBER_DEACTIVATED",
            entity_type="workforce_member",
            entity_id=member.id,
            details_json=json.dumps({"full_name": member.full_name}),
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    db.refresh(member)

    return _format_member_response(member)


@router.post("/members/{member_id}/correct-score", response_model=ScoreHistoryResponse)
def correct_member_performance_score(
    member_id: str,
    payload: ScoreCorrectionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manager-authorized correction of a workforce member's performance score with reason and audit log."""
    _require_delivery_manager(current_user)

    member = (
        db.query(WorkforceMember)
        .filter(WorkforceMember.id == member_id, WorkforceMember.tenant_id == current_user.tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workforce member not found.")

    history = WorkforcePerformanceService.recalculate_member_performance_score(
        db=db,
        tenant_id=current_user.tenant_id,
        member_id=member_id,
        manual_correction={
            "score": payload.corrected_score,
            "reason": payload.reason,
            "user_id": current_user.id,
            "user_email": current_user.email,
        },
    )

    return ScoreHistoryResponse(
        id=history.id,
        tenant_id=history.tenant_id,
        member_id=history.member_id,
        score_version=history.score_version,
        performance_score=history.performance_score,
        has_sufficient_evidence=history.has_sufficient_evidence,
        delivery_score=history.delivery_score,
        quality_score=history.quality_score,
        formula_version=history.formula_version,
        evidence_count=history.evidence_count,
        notes=history.notes,
        is_manual_correction=history.is_manual_correction,
        correction_reason=history.correction_reason,
        corrected_by_user_email=history.corrected_by_user_email,
        created_at=history.created_at,
    )


@router.get("/members/{member_id}/score-history", response_model=List[ScoreHistoryResponse])
def get_member_score_history(
    member_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all versioned score history snapshots for a workforce member."""
    member = (
        db.query(WorkforceMember)
        .filter(WorkforceMember.id == member_id, WorkforceMember.tenant_id == current_user.tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workforce member not found.")

    history = WorkforcePerformanceService.get_member_performance_history(
        db=db, tenant_id=current_user.tenant_id, member_id=member_id
    )
    return [
        ScoreHistoryResponse(
            id=h.id,
            tenant_id=h.tenant_id,
            member_id=h.member_id,
            score_version=h.score_version,
            performance_score=h.performance_score,
            has_sufficient_evidence=h.has_sufficient_evidence,
            delivery_score=h.delivery_score,
            quality_score=h.quality_score,
            formula_version=h.formula_version,
            evidence_count=h.evidence_count,
            notes=h.notes,
            is_manual_correction=h.is_manual_correction,
            correction_reason=h.correction_reason,
            corrected_by_user_email=h.corrected_by_user_email,
            created_at=h.created_at,
        )
        for h in history
    ]


@router.get("/members/{member_id}/evidence", response_model=List[PerformanceEvidenceResponse])
def get_member_performance_evidence(
    member_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves attributable project performance evidence events for a workforce member."""
    member = (
        db.query(WorkforceMember)
        .filter(WorkforceMember.id == member_id, WorkforceMember.tenant_id == current_user.tenant_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workforce member not found.")

    evidence = WorkforcePerformanceService.get_member_performance_evidence(
        db=db, tenant_id=current_user.tenant_id, member_id=member_id
    )
    return [
        PerformanceEvidenceResponse(
            id=e.id,
            tenant_id=e.tenant_id,
            member_id=e.member_id,
            project_id=e.project_id,
            task_id=e.task_id,
            event_fingerprint=e.event_fingerprint,
            event_type=e.event_type,
            planned_hours=e.planned_hours,
            actual_hours=e.actual_hours,
            effort_variance_ratio=e.effort_variance_ratio,
            on_schedule=e.on_schedule,
            was_blocked_externally=e.was_blocked_externally,
            quality_outcome=e.quality_outcome,
            evidence_notes=e.evidence_notes,
            created_at=e.created_at,
        )
        for e in evidence
    ]


@router.post("/recommend/{project_id}", response_model=List[RecommendationResponse])
def generate_recommendations(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates explainable team candidate recommendations for tasks in the project."""
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

    try:
        recs = WorkforceRecommendationService.generate_recommendations_for_project(
            db=db,
            tenant_id=current_user.tenant_id,
            project_id=project_id,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    return [_format_rec_response(db, r) for r in recs]


@router.get("/recommendations/{project_id}", response_model=List[RecommendationResponse])
def get_recommendations(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves existing recommendations for a project, generating if absent."""
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

    recs = (
        db.query(TeamRecommendation)
        .filter(TeamRecommendation.tenant_id == current_user.tenant_id, TeamRecommendation.project_id == project_id)
        .order_by(TeamRecommendation.match_score.desc())
        .all()
    )
    if not recs:
        try:
            recs = WorkforceRecommendationService.generate_recommendations_for_project(
                db=db, tenant_id=current_user.tenant_id, project_id=project_id
            )
        except Exception:
            return []

    return [_format_rec_response(db, r) for r in recs]


@router.post("/recommendations/{rec_id}/approve", response_model=RecommendationResponse)
def approve_recommendation(
    rec_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delivery manager reviews and accepts a proposed workforce recommendation."""
    rec = (
        db.query(TeamRecommendation)
        .filter(TeamRecommendation.id == rec_id, TeamRecommendation.tenant_id == current_user.tenant_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    rec.manager_status = "approved"
    rec.reviewed_at = datetime.utcnow()

    if rec.task_id:
        task = (
            db.query(WBSTask)
            .filter(WBSTask.id == rec.task_id, WBSTask.tenant_id == current_user.tenant_id)
            .first()
        )
        if task:
            task.assigned_user_id = rec.candidate_id
            task.assigned_user_name = rec.candidate_name

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="WORKFORCE_RECOMMENDATION_APPROVED",
            entity_type="team_recommendation",
            entity_id=rec.id,
            details_json=json.dumps({
                "project_id": rec.project_id,
                "task_id": rec.task_id,
                "candidate_id": rec.candidate_id,
                "candidate_name": rec.candidate_name,
            }),
            created_at=datetime.utcnow(),
        )
    )

    db.commit()
    db.refresh(rec)

    return _format_rec_response(db, rec)


@router.post("/recommendations/{rec_id}/reject", response_model=RecommendationResponse)
def reject_recommendation(
    rec_id: str,
    payload: RejectRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delivery manager declines a proposed workforce recommendation with documented rationale."""
    rec = (
        db.query(TeamRecommendation)
        .filter(TeamRecommendation.id == rec_id, TeamRecommendation.tenant_id == current_user.tenant_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    rec.manager_status = "rejected"
    rec.manager_notes = payload.manager_notes or "Declined during manager delivery review."
    rec.reviewed_at = datetime.utcnow()

    if rec.task_id:
        task = (
            db.query(WBSTask)
            .filter(WBSTask.id == rec.task_id, WBSTask.tenant_id == current_user.tenant_id)
            .first()
        )
        if task and task.assigned_user_id == rec.candidate_id:
            task.assigned_user_id = None
            task.assigned_user_name = None

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="WORKFORCE_RECOMMENDATION_REJECTED",
            entity_type="team_recommendation",
            entity_id=rec.id,
            details_json=json.dumps({
                "project_id": rec.project_id,
                "task_id": rec.task_id,
                "candidate_id": rec.candidate_id,
                "candidate_name": rec.candidate_name,
                "manager_notes": rec.manager_notes,
            }),
            created_at=datetime.utcnow(),
        )
    )

    db.commit()
    db.refresh(rec)

    return _format_rec_response(db, rec)


@router.post("/recommendations/{rec_id}/override", response_model=RecommendationResponse)
def override_recommendation(
    rec_id: str,
    payload: OverrideRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delivery manager overrides the recommended candidate with manual selection."""
    rec = (
        db.query(TeamRecommendation)
        .filter(TeamRecommendation.id == rec_id, TeamRecommendation.tenant_id == current_user.tenant_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    prev_id = rec.candidate_id
    prev_name = rec.candidate_name

    rec.candidate_id = payload.candidate_id
    rec.candidate_name = payload.candidate_name
    rec.manager_notes = payload.manager_notes
    rec.manager_status = "overridden"
    rec.reviewed_at = datetime.utcnow()

    if rec.task_id:
        task = (
            db.query(WBSTask)
            .filter(WBSTask.id == rec.task_id, WBSTask.tenant_id == current_user.tenant_id)
            .first()
        )
        if task:
            task.assigned_user_id = payload.candidate_id
            task.assigned_user_name = payload.candidate_name

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="WORKFORCE_RECOMMENDATION_OVERRIDDEN",
            entity_type="team_recommendation",
            entity_id=rec.id,
            details_json=json.dumps({
                "project_id": rec.project_id,
                "task_id": rec.task_id,
                "previous_candidate_id": prev_id,
                "previous_candidate_name": prev_name,
                "new_candidate_id": rec.candidate_id,
                "new_candidate_name": rec.candidate_name,
                "manager_notes": rec.manager_notes,
            }),
            created_at=datetime.utcnow(),
        )
    )

    db.commit()
    db.refresh(rec)

    return _format_rec_response(db, rec)


@router.post("/recommendations/{rec_id}/select-alternative", response_model=RecommendationResponse)
def select_alternative_candidate(
    rec_id: str,
    payload: AlternativeSelectRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delivery manager selects a runner-up candidate directly from the evaluated alternatives list."""
    rec = (
        db.query(TeamRecommendation)
        .filter(TeamRecommendation.id == rec_id, TeamRecommendation.tenant_id == current_user.tenant_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")

    prev_id = rec.candidate_id
    prev_name = rec.candidate_name

    alt_data = None
    if getattr(rec, "alternatives_json", None):
        try:
            alts = json.loads(rec.alternatives_json)
            for a in alts:
                if a.get("candidate_id") == payload.candidate_id:
                    alt_data = a
                    break
        except Exception:
            pass

    if not alt_data:
        member = (
            db.query(WorkforceMember)
            .filter(WorkforceMember.id == payload.candidate_id, WorkforceMember.tenant_id == current_user.tenant_id)
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate '{payload.candidate_id}' not found in alternatives or talent directory.",
            )
        cand_name = member.full_name
        cand_score = 70.0
        cand_rationale = f"Selected from talent directory by delivery manager."
    else:
        cand_name = alt_data["candidate_name"]
        cand_score = alt_data["match_score"]
        cand_rationale = alt_data["rationale"]
        rec.skill_score = alt_data.get("skill_score", rec.skill_score)
        rec.availability_score = alt_data.get("availability_score", rec.availability_score)
        rec.experience_score = alt_data.get("experience_score", rec.experience_score)
        rec.workload_score = alt_data.get("workload_score", rec.workload_score)
        rec.performance_score = alt_data.get("performance_score", getattr(rec, "performance_score", None))

    rec.candidate_id = payload.candidate_id
    rec.candidate_name = cand_name
    rec.match_score = cand_score
    rec.rationale = cand_rationale
    rec.manager_notes = payload.manager_notes or "Selected runner-up alternative from recommendation list."
    rec.manager_status = "approved"
    rec.reviewed_at = datetime.utcnow()

    if rec.task_id:
        task = (
            db.query(WBSTask)
            .filter(WBSTask.id == rec.task_id, WBSTask.tenant_id == current_user.tenant_id)
            .first()
        )
        if task:
            task.assigned_user_id = payload.candidate_id
            task.assigned_user_name = cand_name

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="WORKFORCE_ALTERNATIVE_SELECTED",
            entity_type="team_recommendation",
            entity_id=rec.id,
            details_json=json.dumps({
                "project_id": rec.project_id,
                "task_id": rec.task_id,
                "previous_candidate_id": prev_id,
                "previous_candidate_name": prev_name,
                "selected_candidate_id": rec.candidate_id,
                "selected_candidate_name": rec.candidate_name,
                "manager_notes": rec.manager_notes,
            }),
            created_at=datetime.utcnow(),
        )
    )

    db.commit()
    db.refresh(rec)

    return _format_rec_response(db, rec)


@router.get("/capacity/{project_id}")
def get_project_workforce_capacity(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculates team workload, planned effort, and capacity utilization for the project."""
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

    return WorkforceRecommendationService.calculate_team_workload_and_capacity(
        db=db,
        tenant_id=current_user.tenant_id,
        project_id=project_id,
    )


@router.get("/skill-gaps/{project_id}")
def get_project_skill_gaps(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Conducts forensic skill gap analysis comparing task requirements against talent directory."""
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

    try:
        return WorkforceRecommendationService.analyze_project_skill_gaps(
            db=db,
            tenant_id=current_user.tenant_id,
            project_id=project_id,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
