import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Boolean
from app.core.database import Base


class WorkforceMember(Base):
    """SQLAlchemy model for workforce talent profiles."""

    __tablename__ = "workforce_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    hourly_rate = Column(Float, nullable=False, default=85.0)
    currency = Column(String(10), nullable=False, default="USD")

    skills_json = Column(Text, nullable=False)  # JSON list of skill names
    skill_proficiencies_json = Column(Text, nullable=True)  # JSON dict {skill: proficiency_level}
    experience_years = Column(Float, nullable=False, default=4.0)
    availability_pct = Column(Float, nullable=False, default=100.0)  # 0 to 100
    max_weekly_hours = Column(Float, nullable=False, default=40.0)
    active_projects_count = Column(Integer, nullable=False, default=0)

    # Initial manager evaluation (distinct from historical delivery performance)
    initial_assessed_score = Column(Float, nullable=True)  # e.g., 0-100 initial rating by hiring manager

    # Calibrated delivery performance tracking (None / False if insufficient evidence)
    performance_score = Column(Float, nullable=True)  # Calibrated 0-100 historical delivery score
    has_sufficient_evidence = Column(Boolean, nullable=False, default=False)
    performance_score_version = Column(Integer, nullable=False, default=0)

    # Lifecycle status: active, deactivated
    is_active = Column(Boolean, nullable=False, default=True)
    is_synthetic = Column(Boolean, nullable=False, default=False)  # Clearly labels synthetic benchmarks vs real profiles

    # Creator tracking & enterprise provenance
    created_by_user_id = Column(String(36), nullable=True)
    created_by_user_email = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TeamRecommendation(Base):
    """SQLAlchemy model for explainable team candidate recommendations requiring manager approval."""

    __tablename__ = "team_recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    task_id = Column(String(36), nullable=True)
    role_needed = Column(String(100), nullable=False)

    candidate_id = Column(String(36), nullable=False)
    candidate_name = Column(String(255), nullable=False)

    # Explainable ranking factors
    match_score = Column(Float, nullable=False, default=0.0)        # Composite 0-100
    skill_score = Column(Float, nullable=False, default=0.0)        # 0-100
    availability_score = Column(Float, nullable=False, default=0.0) # 0-100
    experience_score = Column(Float, nullable=False, default=0.0)    # 0-100
    workload_score = Column(Float, nullable=False, default=0.0)      # 0-100
    performance_score = Column(Float, nullable=True)                # Verified delivery performance score if available

    rationale = Column(Text, nullable=False)
    alternatives_json = Column(Text, nullable=True)  # JSON list of runner-up candidate evaluations
    # Manager status: proposed, approved, rejected, overridden
    manager_status = Column(String(30), nullable=False, default="proposed")
    manager_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)


class MemberPerformanceEvidence(Base):
    """SQLAlchemy model for attributable, project-level workforce performance evidence."""

    __tablename__ = "member_performance_evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    member_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    task_id = Column(String(36), nullable=True, index=True)

    # Unique fingerprint ensuring idempotent collection and duplicate prevention
    event_fingerprint = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(50), nullable=False)  # task_completed, milestone_reached, effort_logged

    planned_hours = Column(Float, nullable=False, default=0.0)
    actual_hours = Column(Float, nullable=False, default=0.0)
    effort_variance_ratio = Column(Float, nullable=False, default=1.0)  # actual / planned
    on_schedule = Column(Boolean, nullable=False, default=True)
    was_blocked_externally = Column(Boolean, nullable=False, default=False)
    quality_outcome = Column(String(50), nullable=True)  # clean_delivery, verified_acceptance, blocker_resolved
    evidence_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MemberPerformanceScoreHistory(Base):
    """SQLAlchemy model for immutable performance score version history with contributing evidence and formula versions."""

    __tablename__ = "member_performance_score_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    member_id = Column(String(36), nullable=False, index=True)
    score_version = Column(Integer, nullable=False)

    performance_score = Column(Float, nullable=True)  # None if insufficient evidence
    has_sufficient_evidence = Column(Boolean, nullable=False, default=False)
    delivery_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    formula_version = Column(String(50), nullable=False, default="v2.0-deterministic-outcomes")

    evidence_count = Column(Integer, nullable=False, default=0)
    contributing_evidence_json = Column(Text, nullable=True)  # List of contributing evidence event fingerprints/IDs
    notes = Column(Text, nullable=True)

    # Authorized corrections tracking
    is_manual_correction = Column(Boolean, nullable=False, default=False)
    correction_reason = Column(Text, nullable=True)
    corrected_by_user_id = Column(String(36), nullable=True)
    corrected_by_user_email = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
