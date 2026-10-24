import json
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project
from app.models.wbs import WBSTask, TaskDependency
from app.models.workforce import (
    WorkforceMember,
    TeamRecommendation,
    MemberPerformanceEvidence,
    MemberPerformanceScoreHistory,
)
from app.models.audit import AuditLog
from app.core.security import create_access_token


TEST_TENANT_ID = "tenant-onboard-test"


@pytest.fixture(autouse=True)
def setup_test_tenant(db_session):
    existing = db_session.query(Tenant).filter(Tenant.id == TEST_TENANT_ID).first()
    if not existing:
        t = Tenant(
            id=TEST_TENANT_ID,
            name="Onboarding Test Org",
            slug="onboard-test-org",
            currency="USD",
        )
        db_session.add(t)
        db_session.commit()


@pytest.fixture
def manager_auth_headers():
    token = create_access_token(
        user_id="usr-mgr-test",
        email="manager@devmatrix.test",
        role="delivery_manager",
        tenant_id=TEST_TENANT_ID,
    )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def contributor_auth_headers():
    token = create_access_token(
        user_id="usr-contrib-test",
        email="dev@devmatrix.test",
        role="engineer",
        tenant_id=TEST_TENANT_ID,
    )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def db_session():
    from tests.conftest import TestingSessionLocal
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_manager_only_member_onboarding_and_rbac(manager_auth_headers, contributor_auth_headers):
    """
    Verifies that only authorized delivery managers can onboard team members,
    initial ratings are distinct from performance scores, new members show
    'Insufficient performance history', and audit trails are recorded.
    """
    client = TestClient(app)

    # 1. Non-manager is rejected with 403 Forbidden
    payload = {
        "full_name": "Maya Lin",
        "role": "Frontend UI/UX Specialist",
        "hourly_rate": 115.0,
        "skills": ["React", "TypeScript", "TailwindCSS"],
        "skill_proficiencies": {"React": "expert", "TypeScript": "advanced"},
        "experience_years": 5.0,
        "availability_pct": 100.0,
        "max_weekly_hours": 40.0,
        "initial_assessed_score": 88.0,
    }
    forbidden_resp = client.post("/api/workforce", headers=contributor_auth_headers, json=payload)
    assert forbidden_resp.status_code == 403
    assert "manager role required" in forbidden_resp.json()["detail"].lower()

    # 2. Authorized delivery manager successfully onboards persistent member
    create_resp = client.post("/api/workforce", headers=manager_auth_headers, json=payload)
    assert create_resp.status_code == 201
    member = create_resp.json()

    assert member["full_name"] == "Maya Lin"
    assert member["role"] == "Frontend UI/UX Specialist"
    assert member["hourly_rate"] == 115.0
    assert member["skills"] == ["React", "TypeScript", "TailwindCSS"]
    assert member["skill_proficiencies"] == {"React": "expert", "TypeScript": "advanced"}
    assert member["initial_assessed_score"] == 88.0

    # Critical requirement: New member shows "Insufficient performance history", not invented score
    assert member["performance_score"] is None
    assert member["has_sufficient_evidence"] is False
    assert member["performance_status_label"] == "Insufficient performance history"
    assert member["performance_score_version"] == 0
    assert member["is_active"] is True
    assert member["is_synthetic"] is False
    assert member["created_by_user_email"] == "manager@devmatrix.test"

    # Verify audit log was recorded
    audit_resp = client.get("/api/admin/audit-logs", headers=manager_auth_headers)
    if audit_resp.status_code == 200:
        logs = [
            l for l in audit_resp.json()
            if l.get("action") == "WORKFORCE_MEMBER_CREATED" and l.get("entity_id") == member["id"]
        ]
        assert len(logs) >= 1
        assert "Maya Lin" in str(logs[0]["details"])


def test_member_edit_activation_and_deactivation_lifecycle(manager_auth_headers, contributor_auth_headers):
    """
    Verifies that managers can edit, deactivate, and reactivate member profiles.
    Inactive members must be excluded from subsequent recommendation rankings.
    """
    client = TestClient(app)

    # Onboard member
    create_resp = client.post(
        "/api/workforce",
        headers=manager_auth_headers,
        json={
            "full_name": "Jordan Rivera",
            "role": "Cloud DevOps Architect",
            "hourly_rate": 140.0,
            "skills": ["AWS", "Terraform", "Kubernetes"],
            "experience_years": 8.0,
            "availability_pct": 80.0,
            "max_weekly_hours": 40.0,
            "initial_assessed_score": 92.0,
        },
    )
    assert create_resp.status_code == 201
    m_id = create_resp.json()["id"]

    # 1. Non-manager cannot update
    upd_resp = client.put(f"/api/workforce/members/{m_id}", headers=contributor_auth_headers, json={"hourly_rate": 150.0})
    assert upd_resp.status_code == 403

    # 2. Manager updates member profile
    upd_resp = client.put(
        f"/api/workforce/members/{m_id}",
        headers=manager_auth_headers,
        json={"hourly_rate": 150.0, "experience_years": 9.0},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["hourly_rate"] == 150.0
    assert upd_resp.json()["experience_years"] == 9.0

    # 3. Manager deactivates member profile
    deact_resp = client.post(f"/api/workforce/members/{m_id}/deactivate", headers=manager_auth_headers)
    assert deact_resp.status_code == 200
    assert deact_resp.json()["is_active"] is False

    # Check list endpoint default excludes inactive
    list_active = client.get("/api/workforce", headers=manager_auth_headers).json()
    assert not any(m["id"] == m_id for m in list_active)

    # Check list endpoint with include_inactive=True
    list_all = client.get("/api/workforce?include_inactive=true", headers=manager_auth_headers).json()
    assert any(m["id"] == m_id for m in list_all)

    # 4. Manager reactivates member profile
    act_resp = client.post(f"/api/workforce/members/{m_id}/activate", headers=manager_auth_headers)
    assert act_resp.status_code == 200
    assert act_resp.json()["is_active"] is True


def test_automatic_performance_evidence_and_duplicate_prevention(manager_auth_headers, db_session):
    """
    Verifies that task updates automatically generate attributable performance evidence,
    subsequent duplicate updates do not create duplicate events, and external blockers
    protect contributors from penalty.
    """
    client = TestClient(app)

    # Setup project and member
    proj_id = f"test-perf-proj-{uuid.uuid4().hex[:8]}"
    project = Project(
        id=proj_id,
        tenant_id=TEST_TENANT_ID,
        name="Performance Tracking Verification Project",
        status="active",
        currency="USD",
    )
    db_session.add(project)

    member = WorkforceMember(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        full_name="Marcus Vance",
        role="Backend Python Engineer",
        hourly_rate=110.0,
        currency="USD",
        skills_json=json.dumps(["Python", "FastAPI", "PostgreSQL"]),
        experience_years=6.0,
        availability_pct=100.0,
        max_weekly_hours=40.0,
        performance_score=None,
        has_sufficient_evidence=False,
        is_active=True,
    )
    db_session.add(member)

    # Create task with external blocker note
    task_id = str(uuid.uuid4())
    task = WBSTask(
        id=task_id,
        tenant_id=TEST_TENANT_ID,
        project_id=proj_id,
        task_code="TSK-PERF-01",
        title="Async Event Consumer Pipeline",
        required_role="Backend Python Engineer",
        assigned_user_id=member.id,
        assigned_user_name=member.full_name,
        expected_hours=20.0,
        actual_hours=0.0,
        status="in_progress",
        blocker_notes="Blocked for 3 days due to external cloud credential provisioning delay",
    )
    db_session.add(task)
    db_session.commit()

    # Complete the task via task update API
    update_payload = {
        "task_id": task_id,
        "hours_logged": 28.0,  # 28h vs 20h planned due to external delay
        "new_status": "completed",
        "progress_percentage": 100.0,
        "progress_notes": "Completed following resolution of credential delay",
    }
    resp1 = client.post("/api/execution/task-update", headers=manager_auth_headers, json=update_payload)
    assert resp1.status_code == 200

    # 1. Verify attributable evidence record was created
    ev_resp = client.get(f"/api/workforce/members/{member.id}/evidence", headers=manager_auth_headers)
    assert ev_resp.status_code == 200
    evidence = ev_resp.json()
    assert len(evidence) >= 1
    target_ev = next(e for e in evidence if e["task_id"] == task_id)
    assert target_ev["event_type"] == "task_completed"
    assert target_ev["actual_hours"] == 28.0
    assert target_ev["planned_hours"] == 20.0
    assert target_ev["was_blocked_externally"] is True  # Protected from penalty!

    # 2. Duplicate Prevention: Attempting another update for the completed task must NOT duplicate evidence
    client.post("/api/execution/task-update", headers=manager_auth_headers, json=update_payload)
    ev_resp2 = client.get(f"/api/workforce/members/{member.id}/evidence", headers=manager_auth_headers).json()
    assert len([e for e in ev_resp2 if e["task_id"] == task_id and e["event_type"] == "task_completed"]) == 1

    # 3. Check automatic score calculation
    db_session.refresh(member)
    assert member.has_sufficient_evidence is True
    assert member.performance_score is not None
    # Because was_blocked_externally was True, score is normalized without overrun penalty (90.0 delivery + 88.0 quality = 89.0)
    assert member.performance_score >= 85.0


def test_score_version_history_and_authorized_corrections(manager_auth_headers, db_session):
    """
    Verifies that score history preserves previous versions, contributing evidence,
    and authorized manager corrections with audit logs.
    """
    client = TestClient(app)

    member = WorkforceMember(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        full_name="Samantha Ray",
        role="QA Automation Engineer",
        hourly_rate=95.0,
        currency="USD",
        skills_json=json.dumps(["Playwright", "Python", "CI/CD"]),
        experience_years=4.0,
        availability_pct=90.0,
        max_weekly_hours=40.0,
        performance_score=85.0,
        has_sufficient_evidence=True,
        performance_score_version=1,
        is_active=True,
    )
    db_session.add(member)
    db_session.commit()

    # Authorized manager applies a score correction
    correction_payload = {
        "corrected_score": 93.5,
        "reason": "Post-delivery retrospective confirmed excellence in zero-defect test suite delivery.",
    }
    corr_resp = client.post(
        f"/api/workforce/members/{member.id}/correct-score",
        headers=manager_auth_headers,
        json=correction_payload,
    )
    assert corr_resp.status_code == 200
    corr_data = corr_resp.json()
    assert corr_data["score_version"] == 2
    assert corr_data["performance_score"] == 93.5
    assert corr_data["is_manual_correction"] is True
    assert "retrospective" in corr_data["correction_reason"]

    # Verify score history endpoint
    hist_resp = client.get(f"/api/workforce/members/{member.id}/score-history", headers=manager_auth_headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) >= 1
    assert history[0]["score_version"] == 2
    assert history[0]["performance_score"] == 93.5


def test_recorded_project_outcome_changes_performance_score_and_influences_subsequent_recommendation(
    manager_auth_headers, db_session
):
    """
    CRITICAL WORKFLOW TEST:
    Demonstrates that a recorded project task outcome:
    1. Updates a member's performance score automatically.
    2. Directly improves their ranking in subsequent project team recommendations,
       elevating them above an otherwise identical peer who lacks verified delivery history.
    """
    client = TestClient(app)

    # 1. Create two contributors with identical role, skills, experience, and availability
    member_a = WorkforceMember(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        full_name="Alice Engineer (Proven Delivery)",
        role="Full-Stack Engineer",
        hourly_rate=100.0,
        currency="USD",
        skills_json=json.dumps(["Full-Stack Engineer", "Python", "React", "SQL"]),
        experience_years=5.0,
        availability_pct=100.0,
        max_weekly_hours=40.0,
        active_projects_count=0,
        performance_score=None,
        has_sufficient_evidence=False,
        performance_score_version=0,
        is_active=True,
    )
    member_b = WorkforceMember(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        full_name="Bob Engineer (Unverified Baseline)",
        role="Full-Stack Engineer",
        hourly_rate=100.0,
        currency="USD",
        skills_json=json.dumps(["Full-Stack Engineer", "Python", "React", "SQL"]),
        experience_years=5.0,
        availability_pct=100.0,
        max_weekly_hours=40.0,
        active_projects_count=0,
        performance_score=None,
        has_sufficient_evidence=False,
        performance_score_version=0,
        is_active=True,
    )
    db_session.add_all([member_a, member_b])

    # 2. Project 1: Member A completes a deliverable on time and under budget
    p1_id = f"proj1-{uuid.uuid4().hex[:8]}"
    project_1 = Project(
        id=p1_id,
        tenant_id=TEST_TENANT_ID,
        name="Project 1 — Initial Delivery",
        status="active",
        currency="USD",
    )
    db_session.add(project_1)

    task_p1 = WBSTask(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        project_id=p1_id,
        task_code="TSK-P1-01",
        title="Core Module Implementation",
        required_role="Full-Stack Engineer",
        assigned_user_id=member_a.id,
        assigned_user_name=member_a.full_name,
        expected_hours=16.0,
        actual_hours=0.0,
        status="in_progress",
    )
    db_session.add(task_p1)
    db_session.commit()

    # Log task completion for Member A (delivered in 15h vs 16h expected)
    task_update_resp = client.post(
        "/api/execution/task-update",
        headers=manager_auth_headers,
        json={
            "task_id": task_p1.id,
            "hours_logged": 15.0,
            "new_status": "completed",
            "progress_percentage": 100.0,
            "progress_notes": "Delivered ahead of schedule with all acceptance criteria met.",
        },
    )
    assert task_update_resp.status_code == 200

    # Verify Member A's performance score is automatically updated to 100.0%
    db_session.refresh(member_a)
    assert member_a.has_sufficient_evidence is True
    assert member_a.performance_score == 100.0
    assert member_a.performance_score_version >= 1

    # Verify Member B remains unverified baseline (no history)
    db_session.refresh(member_b)
    assert member_b.has_sufficient_evidence is False
    assert member_b.performance_score is None

    # 3. Project 2: Create a second project with a WBS task requiring a Full-Stack Engineer
    p2_id = f"proj2-{uuid.uuid4().hex[:8]}"
    project_2 = Project(
        id=p2_id,
        tenant_id=TEST_TENANT_ID,
        name="Project 2 — Next Delivery",
        status="active",
        currency="USD",
    )
    db_session.add(project_2)

    task_p2 = WBSTask(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        project_id=p2_id,
        task_code="TSK-P2-01",
        title="Next-Gen API Service",
        required_role="Full-Stack Engineer",
        expected_hours=24.0,
        actual_hours=0.0,
        status="not_started",
    )
    db_session.add(task_p2)
    db_session.commit()

    # 4. Generate recommendations for Project 2
    rec_resp = client.post(f"/api/workforce/recommend/{p2_id}", headers=manager_auth_headers)
    assert rec_resp.status_code == 200
    recs = rec_resp.json()
    assert len(recs) >= 1

    rec_task2 = next(r for r in recs if r["task_code"] == "TSK-P2-01")

    # Member A MUST be the top recommended candidate because of the verified 100% performance history!
    assert rec_task2["candidate_id"] == member_a.id
    assert rec_task2["candidate_name"] == member_a.full_name
    assert rec_task2["performance_score"] == 100.0
    assert "Verified delivery performance: 100.0%" in rec_task2["rationale"]

    # Member B is an alternative with lower composite match score because of unverified baseline history
    alts = rec_task2["alternatives"]
    assert any(a["candidate_id"] == member_b.id for a in alts)
    alt_b = next(a for a in alts if a["candidate_id"] == member_b.id)
    assert rec_task2["match_score"] > alt_b["match_score"]
    assert "Insufficient performance history" in alt_b["rationale"]
