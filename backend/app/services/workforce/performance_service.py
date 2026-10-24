import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.workforce import (
    WorkforceMember,
    MemberPerformanceEvidence,
    MemberPerformanceScoreHistory,
)
from app.models.wbs import WBSTask, TaskDependency
from app.models.execution import TaskUpdateRecord
from app.models.audit import AuditLog


class WorkforcePerformanceService:
    """
    Service for attributable workforce performance evidence collection,
    transparent deterministic score calculation, versioned score history,
    and automatic score updates upon project outcomes.
    """

    FORMULA_VERSION = "v2.0-deterministic-outcomes"

    @classmethod
    def record_task_outcome_evidence(
        cls,
        db: Session,
        tenant_id: str,
        task: WBSTask,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        override_event_type: Optional[str] = None,
    ) -> Optional[MemberPerformanceEvidence]:
        """
        Extracts attributable, project-specific performance evidence from a task outcome.
        Prevents duplicate events using a deterministic event fingerprint.
        Protects contributors from penalty if tasks were delayed by external blockers.
        Automatically updates member performance score upon recording meaningful evidence.
        """
        # Resolve assigned workforce member
        member = None
        if task.assigned_user_id:
            member = (
                db.query(WorkforceMember)
                .filter(
                    WorkforceMember.id == task.assigned_user_id,
                    WorkforceMember.tenant_id == tenant_id,
                )
                .first()
            )
        if not member and task.assigned_user_name:
            member = (
                db.query(WorkforceMember)
                .filter(
                    WorkforceMember.full_name == task.assigned_user_name,
                    WorkforceMember.tenant_id == tenant_id,
                )
                .first()
            )

        if not member:
            return None

        event_type = override_event_type or ("task_completed" if task.status == "completed" else "effort_logged")

        # Deterministic event fingerprint prevents double-counting duplicate updates
        if event_type == "task_completed":
            fingerprint = f"{tenant_id}:{task.project_id}:{task.id}:completed"
        else:
            fingerprint = f"{tenant_id}:{task.project_id}:{task.id}:effort:{round(task.actual_hours, 1)}"

        existing_evidence = (
            db.query(MemberPerformanceEvidence)
            .filter(MemberPerformanceEvidence.event_fingerprint == fingerprint)
            .first()
        )
        if existing_evidence:
            return existing_evidence

        planned = float(task.expected_hours or 0.0)
        actual = float(task.actual_hours or 0.0)
        variance_ratio = round(actual / planned, 2) if planned > 0 else 1.0

        # Detect external blockers: check task blocker notes, update records, and predecessor dependencies
        has_blocker_notes = bool(task.blocker_notes and task.blocker_notes.strip())
        past_records = (
            db.query(TaskUpdateRecord)
            .filter(TaskUpdateRecord.task_id == task.id)
            .all()
        )
        had_blocker_record = any(
            r.blocker_flag == "true"
            or bool(r.blocker_description and r.blocker_description.strip())
            or bool(r.progress_notes and any(kw in r.progress_notes.lower() for kw in ("delay", "blocked", "blocker", "waiting on", "external", "credential")))
            for r in past_records
        )
        # Check if any predecessor dependency is or was blocked
        pred_blocked = False
        deps = (
            db.query(TaskDependency)
            .filter(TaskDependency.successor_task_id == task.id)
            .all()
        )
        for dep in deps:
            pred = db.query(WBSTask).filter(WBSTask.id == dep.predecessor_task_id).first()
            if pred and (pred.status == "blocked" or pred.blocker_notes):
                pred_blocked = True
                break

        was_blocked_externally = has_blocker_notes or had_blocker_record or pred_blocked

        # Delivery on-schedule: true if under 1.25x PERT expectation or if delayed by external blocker
        on_schedule = (variance_ratio <= 1.25) or was_blocked_externally

        if was_blocked_externally:
            quality_outcome = "blocker_resolved" if task.status == "completed" else "blocker_incurred"
            notes = f"Task {task.task_code} completed with documented external dependency delays. Protected from performance penalty."
        else:
            quality_outcome = "clean_delivery" if task.status == "completed" else "standard_progress"
            notes = f"Task {task.task_code} delivered with {actual}h actual effort vs {planned}h PERT planned expectation."

        evidence = MemberPerformanceEvidence(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            member_id=member.id,
            project_id=task.project_id,
            task_id=task.id,
            event_fingerprint=fingerprint,
            event_type=event_type,
            planned_hours=planned,
            actual_hours=actual,
            effort_variance_ratio=variance_ratio,
            on_schedule=on_schedule,
            was_blocked_externally=was_blocked_externally,
            quality_outcome=quality_outcome,
            evidence_notes=notes,
            created_at=datetime.utcnow(),
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        # Trigger automatic score update for the member
        cls.recalculate_member_performance_score(
            db=db,
            tenant_id=tenant_id,
            member_id=member.id,
            trigger_reason=f"Automatic update upon {event_type} on {task.task_code}",
        )

        return evidence

    @classmethod
    def recalculate_member_performance_score(
        cls,
        db: Session,
        tenant_id: str,
        member_id: str,
        trigger_reason: Optional[str] = None,
        manual_correction: Optional[Dict[str, Any]] = None,
    ) -> MemberPerformanceScoreHistory:
        """
        Recalculates a member's performance score deterministically using all attributable evidence.
        Distinguishes new members with 'Insufficient performance history' from low performers.
        Preserves score version history, contributing evidence, and formula version.
        Supports authorized manager corrections with audit trail.
        """
        member = (
            db.query(WorkforceMember)
            .filter(WorkforceMember.id == member_id, WorkforceMember.tenant_id == tenant_id)
            .first()
        )
        if not member:
            raise ValueError(f"Workforce member '{member_id}' not found.")

        evidence_list = (
            db.query(MemberPerformanceEvidence)
            .filter(
                MemberPerformanceEvidence.tenant_id == tenant_id,
                MemberPerformanceEvidence.member_id == member_id,
            )
            .order_by(MemberPerformanceEvidence.created_at.asc())
            .all()
        )

        next_version = (member.performance_score_version or 0) + 1

        # Case 1: Manual Correction by authorized manager
        if manual_correction:
            new_score = round(float(manual_correction["score"]), 1)
            reason = manual_correction.get("reason", "Authorized delivery manager correction")
            user_id = manual_correction.get("user_id")
            user_email = manual_correction.get("user_email")

            history = MemberPerformanceScoreHistory(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                member_id=member_id,
                score_version=next_version,
                performance_score=new_score,
                has_sufficient_evidence=True,
                delivery_score=new_score,
                quality_score=new_score,
                formula_version=cls.FORMULA_VERSION,
                evidence_count=len(evidence_list),
                contributing_evidence_json=json.dumps([e.id for e in evidence_list]),
                notes=f"Manual correction applied: {reason}",
                is_manual_correction=True,
                correction_reason=reason,
                corrected_by_user_id=user_id,
                corrected_by_user_email=user_email,
                created_at=datetime.utcnow(),
            )
            db.add(history)

            member.performance_score = new_score
            member.has_sufficient_evidence = True
            member.performance_score_version = next_version
            member.updated_at = datetime.utcnow()

            db.add(
                AuditLog(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_email=user_email,
                    action="WORKFORCE_SCORE_CORRECTED",
                    entity_type="workforce_member",
                    entity_id=member.id,
                    details_json=json.dumps({
                        "member_name": member.full_name,
                        "new_score": new_score,
                        "score_version": next_version,
                        "reason": reason,
                    }),
                    created_at=datetime.utcnow(),
                )
            )

            db.commit()
            db.refresh(member)
            return history

        # Case 2: Insufficient performance history (New Member)
        # Filter for meaningful outcomes (e.g. task_completed or milestone)
        meaningful_outcomes = [e for e in evidence_list if e.event_type in ("task_completed", "milestone_reached")]

        if not meaningful_outcomes:
            history = MemberPerformanceScoreHistory(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                member_id=member_id,
                score_version=next_version,
                performance_score=None,
                has_sufficient_evidence=False,
                delivery_score=None,
                quality_score=None,
                formula_version=cls.FORMULA_VERSION,
                evidence_count=len(evidence_list),
                contributing_evidence_json=json.dumps([e.id for e in evidence_list]),
                notes="Insufficient performance history (baseline onboarding assessment). No completed deliverables recorded yet.",
                is_manual_correction=False,
                created_at=datetime.utcnow(),
            )
            db.add(history)

            member.performance_score = None
            member.has_sufficient_evidence = False
            member.performance_score_version = next_version
            member.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(member)
            return history

        # Case 3: Automatic Deterministic Performance Scoring Formula
        delivery_scores = []
        quality_scores = []

        for ev in meaningful_outcomes:
            ratio = ev.effort_variance_ratio
            if ev.was_blocked_externally:
                # Protected from penalty: normalized score 90.0
                delivery_scores.append(90.0)
            elif ratio <= 1.0:
                # Delivered on or under PERT expectation: 100 points
                delivery_scores.append(100.0)
            elif ratio <= 1.5:
                # Gradual decrease from 100 down to 60 based on overrun
                score = 100.0 - ((ratio - 1.0) * 80.0)
                delivery_scores.append(max(60.0, score))
            else:
                # Significant overrun without documented blocker: 50 points
                delivery_scores.append(50.0)

            # Quality score
            if ev.quality_outcome == "clean_delivery":
                quality_scores.append(100.0)
            elif ev.quality_outcome == "blocker_resolved":
                quality_scores.append(88.0)
            else:
                quality_scores.append(80.0)

        avg_delivery = sum(delivery_scores) / len(delivery_scores) if delivery_scores else 80.0
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 80.0

        # Weighted formula: 50% Delivery Accuracy + 50% Quality Completion
        final_score = round((0.50 * avg_delivery) + (0.50 * avg_quality), 1)
        final_score = min(100.0, max(20.0, final_score))

        notes = (
            f"Automatically calibrated from {len(meaningful_outcomes)} completed deliverable outcome(s). "
            f"Delivery Accuracy: {avg_delivery:.1f}%, Quality: {avg_quality:.1f}%."
        )
        if trigger_reason:
            notes += f" Trigger: {trigger_reason}."

        history = MemberPerformanceScoreHistory(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            member_id=member_id,
            score_version=next_version,
            performance_score=final_score,
            has_sufficient_evidence=True,
            delivery_score=round(avg_delivery, 1),
            quality_score=round(avg_quality, 1),
            formula_version=cls.FORMULA_VERSION,
            evidence_count=len(meaningful_outcomes),
            contributing_evidence_json=json.dumps([e.id for e in meaningful_outcomes]),
            notes=notes,
            is_manual_correction=False,
            created_at=datetime.utcnow(),
        )
        db.add(history)

        member.performance_score = final_score
        member.has_sufficient_evidence = True
        member.performance_score_version = next_version
        member.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(member)

        return history

    @classmethod
    def get_member_performance_history(
        cls,
        db: Session,
        tenant_id: str,
        member_id: str,
    ) -> List[MemberPerformanceScoreHistory]:
        """Retrieves all versioned performance score snapshots for a member."""
        return (
            db.query(MemberPerformanceScoreHistory)
            .filter(
                MemberPerformanceScoreHistory.tenant_id == tenant_id,
                MemberPerformanceScoreHistory.member_id == member_id,
            )
            .order_by(MemberPerformanceScoreHistory.score_version.desc())
            .all()
        )

    @classmethod
    def get_member_performance_evidence(
        cls,
        db: Session,
        tenant_id: str,
        member_id: str,
    ) -> List[MemberPerformanceEvidence]:
        """Retrieves attributable project performance evidence events for a member."""
        return (
            db.query(MemberPerformanceEvidence)
            .filter(
                MemberPerformanceEvidence.tenant_id == tenant_id,
                MemberPerformanceEvidence.member_id == member_id,
            )
            .order_by(MemberPerformanceEvidence.created_at.desc())
            .all()
        )
