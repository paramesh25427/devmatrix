import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.project import Project
from app.models.wbs import WBSTask
from app.models.execution import ProjectMilestone, TaskUpdateRecord
from app.models.audit import AuditLog
from tests.conftest import TestingSessionLocal


client = TestClient(app)


def test_valid_status_and_progress_lifecycle(auth_headers_tenant_a):
    db = TestingSessionLocal()
    proj_id = f"test-exec-{uuid.uuid4()}"
    t_id = f"task-{uuid.uuid4()}"
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Execution Lifecycle Demo",
            status="intake",
        )
        task = WBSTask(
            id=t_id,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-01",
            title="Design Service Mesh Architecture",
            required_role="Solutions Architect",
            status="not_started",
            progress_percentage=0.0,
            expected_hours=20.0,
            actual_hours=0.0,
        )
        db.add(proj)
        db.add(task)
        db.commit()

        # 1. Update from not_started to in_progress with 50% progress and 6.0 hours logged
        res1 = client.post(
            "/api/execution/task-update",
            json={
                "task_id": t_id,
                "new_status": "in_progress",
                "progress_percentage": 50.0,
                "hours_logged": 6.0,
                "progress_notes": "Completed initial architectural blueprint",
            },
            headers=auth_headers_tenant_a,
        )
        assert res1.status_code == 200, res1.text
        data1 = res1.json()
        assert data1["new_status"] == "in_progress"
        assert data1["progress_percentage"] == 50.0
        assert data1["actual_hours"] == 6.0

        # Verify database record
        t1 = db.query(WBSTask).filter(WBSTask.id == t_id).first()
        assert t1.status == "in_progress"
        assert t1.progress_percentage == 50.0
        assert t1.actual_hours == 6.0

        # 2. Update to completed (should automatically synchronize progress to 100%)
        res2 = client.post(
            "/api/execution/task-update",
            json={
                "task_id": t_id,
                "new_status": "completed",
                "hours_logged": 8.0,
                "progress_notes": "Review passed by Lead Architect",
            },
            headers=auth_headers_tenant_a,
        )
        assert res2.status_code == 200, res2.text
        data2 = res2.json()
        assert data2["new_status"] == "completed"
        assert data2["progress_percentage"] == 100.0
        assert data2["actual_hours"] == 14.0

        db.expire_all()
        t2 = db.query(WBSTask).filter(WBSTask.id == t_id).first()
        assert t2.status == "completed"
        assert t2.progress_percentage == 100.0
        assert t2.actual_hours == 14.0
    finally:
        db.query(TaskUpdateRecord).filter(TaskUpdateRecord.project_id == proj_id).delete()
        db.query(AuditLog).filter(AuditLog.entity_id == t_id).delete()
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_input_validations_and_rejections(auth_headers_tenant_a):
    db = TestingSessionLocal()
    proj_id = f"test-exec-{uuid.uuid4()}"
    t_id = f"task-{uuid.uuid4()}"
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Validation Test Project",
            status="intake",
        )
        task = WBSTask(
            id=t_id,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-VAL",
            title="Input Validation Task",
            required_role="Full-Stack Engineer",
            status="not_started",
            expected_hours=10.0,
            actual_hours=0.0,
        )
        db.add(proj)
        db.add(task)
        db.commit()

        # Reject negative hours logged
        neg_res = client.post(
            "/api/execution/task-update",
            json={"task_id": t_id, "new_status": "in_progress", "hours_logged": -5.0},
            headers=auth_headers_tenant_a,
        )
        assert neg_res.status_code == 400
        assert "negative" in neg_res.json()["detail"].lower()

        # Reject invalid status
        inv_stat = client.post(
            "/api/execution/task-update",
            json={"task_id": t_id, "new_status": "invalid_status", "hours_logged": 2.0},
            headers=auth_headers_tenant_a,
        )
        assert inv_stat.status_code == 400
        assert "invalid task status" in inv_stat.json()["detail"].lower()

        # Reject out-of-range progress percentage (> 100)
        high_prog = client.post(
            "/api/execution/task-update",
            json={"task_id": t_id, "new_status": "in_progress", "progress_percentage": 150.0},
            headers=auth_headers_tenant_a,
        )
        assert high_prog.status_code == 400
        assert "between 0.0 and 100.0" in high_prog.json()["detail"].lower()

        # Reject negative progress percentage (< 0)
        low_prog = client.post(
            "/api/execution/task-update",
            json={"task_id": t_id, "new_status": "in_progress", "progress_percentage": -10.0},
            headers=auth_headers_tenant_a,
        )
        assert low_prog.status_code == 400
        assert "between 0.0 and 100.0" in low_prog.json()["detail"].lower()

        # Reject blocked status without description when task has no existing blocker notes
        block_res = client.post(
            "/api/execution/task-update",
            json={"task_id": t_id, "new_status": "blocked", "blocker_description": ""},
            headers=auth_headers_tenant_a,
        )
        assert block_res.status_code == 400
        assert "blocker description is required" in block_res.json()["detail"].lower()
    finally:
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_audit_trail_recorded(auth_headers_tenant_a):
    db = TestingSessionLocal()
    proj_id = f"test-exec-{uuid.uuid4()}"
    t_id = f"task-{uuid.uuid4()}"
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Audit Test Project",
            status="intake",
        )
        task = WBSTask(
            id=t_id,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-AUD",
            title="Audit Verification Task",
            required_role="QA Automation Specialist",
            status="not_started",
            expected_hours=8.0,
            actual_hours=0.0,
        )
        db.add(proj)
        db.add(task)
        db.commit()

        res = client.post(
            "/api/execution/task-update",
            json={
                "task_id": t_id,
                "new_status": "in_progress",
                "progress_percentage": 25.0,
                "hours_logged": 3.5,
                "progress_notes": "Implemented test runner skeleton",
            },
            headers=auth_headers_tenant_a,
        )
        assert res.status_code == 200

        # Verify TaskUpdateRecord
        rec = db.query(TaskUpdateRecord).filter(TaskUpdateRecord.task_id == t_id).first()
        assert rec is not None
        assert rec.previous_status == "not_started"
        assert rec.new_status == "in_progress"
        assert rec.hours_logged == 3.5
        assert rec.progress_percentage == 25.0
        assert rec.progress_notes == "Implemented test runner skeleton"

        # Verify AuditLog
        audit = db.query(AuditLog).filter(AuditLog.entity_id == t_id, AuditLog.action == "UPDATE_TASK_PROGRESS").first()
        assert audit is not None
        assert audit.tenant_id == "tenant-default"
        assert audit.user_email == "manager@devmatrix.local"
    finally:
        db.query(TaskUpdateRecord).filter(TaskUpdateRecord.project_id == proj_id).delete()
        db.query(AuditLog).filter(AuditLog.entity_id == t_id).delete()
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_execution_summary_aggregates_and_overdue(auth_headers_tenant_a):
    db = TestingSessionLocal()
    proj_id = f"test-exec-{uuid.uuid4()}"
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Aggregates Test Project",
            status="intake",
        )
        db.add(proj)

        # 3 tasks: 1 completed (100%), 1 in_progress (50%), 1 blocked (20%)
        t1 = WBSTask(
            id=f"t1-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-1",
            title="Task 1",
            status="completed",
            progress_percentage=100.0,
            expected_hours=10.0,
            actual_hours=10.0,
        )
        t2 = WBSTask(
            id=f"t2-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-2",
            title="Task 2",
            status="in_progress",
            progress_percentage=50.0,
            expected_hours=20.0,
            actual_hours=8.0,
        )
        t3 = WBSTask(
            id=f"t3-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-3",
            title="Task 3",
            status="blocked",
            progress_percentage=20.0,
            expected_hours=30.0,
            actual_hours=5.0,
            blocker_notes="Awaiting third-party API credentials",
        )
        db.add_all([t1, t2, t3])

        # Milestones: 1 overdue (due yesterday, pending), 1 future (completed)
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")
        m1 = ProjectMilestone(
            id=f"m1-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            title="Alpha Milestone",
            due_date=yesterday,
            status="pending",
        )
        m2 = ProjectMilestone(
            id=f"m2-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            title="Beta Milestone",
            due_date=tomorrow,
            status="completed",
        )
        db.add_all([m1, m2])
        db.commit()

        res = client.get(f"/api/execution/summary/{proj_id}", headers=auth_headers_tenant_a)
        assert res.status_code == 200, res.text
        summary = res.json()

        assert summary["total_tasks"] == 3
        assert summary["completed_tasks"] == 1
        assert summary["in_progress_tasks"] == 1
        assert summary["blocked_tasks"] == 1
        # Project-level completion: (100 + 50 + 20) / 3 = 170 / 3 = 56.7%
        assert summary["completion_percentage"] == 56.7
        assert summary["total_planned_hours"] == 60.0
        assert summary["total_actual_hours"] == 23.0
        assert summary["overdue_milestones_count"] == 1
        assert len(summary["active_blockers"]) == 1
        assert summary["active_blockers"][0]["task_code"] == "TSK-3"
        assert summary["active_blockers"][0]["notes"] == "Awaiting third-party API credentials"

        # Also verify /api/execution/tasks endpoint
        tasks_res = client.get(f"/api/execution/tasks/{proj_id}", headers=auth_headers_tenant_a)
        assert tasks_res.status_code == 200
        tasks_data = tasks_res.json()
        assert len(tasks_data) == 3
        assert any(t["task_code"] == "TSK-1" and t["progress_percentage"] == 100.0 for t in tasks_data)
        assert any(t["task_code"] == "TSK-2" and t["progress_percentage"] == 50.0 for t in tasks_data)
    finally:
        db.query(ProjectMilestone).filter(ProjectMilestone.project_id == proj_id).delete()
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_tenant_and_project_isolation(auth_headers_tenant_a, token_manager_b):
    db = TestingSessionLocal()
    proj_a = f"proj-a-{uuid.uuid4()}"
    t_a = f"task-a-{uuid.uuid4()}"
    other_tenant_auth = {"Authorization": f"Bearer {token_manager_b}"}
    try:
        proj = Project(
            id=proj_a,
            tenant_id="tenant-default",
            name="Tenant A Isolated Project",
            status="intake",
        )
        task = WBSTask(
            id=t_a,
            tenant_id="tenant-default",
            project_id=proj_a,
            task_code="TSK-ISO",
            title="Isolated Task",
            expected_hours=10.0,
        )
        db.add(proj)
        db.add(task)
        db.commit()

        # Other tenant cannot read summary
        res_summary = client.get(f"/api/execution/summary/{proj_a}", headers=other_tenant_auth)
        assert res_summary.status_code == 404

        # Other tenant cannot read execution tasks
        res_tasks = client.get(f"/api/execution/tasks/{proj_a}", headers=other_tenant_auth)
        assert res_tasks.status_code == 404

        # Other tenant cannot update task
        res_update = client.post(
            "/api/execution/task-update",
            json={"task_id": t_a, "new_status": "completed"},
            headers=other_tenant_auth,
        )
        assert res_update.status_code == 404

        # Updating nonexistent task returns 404
        res_nonexistent = client.post(
            "/api/execution/task-update",
            json={"task_id": "nonexistent-task-id", "new_status": "completed"},
            headers=auth_headers_tenant_a,
        )
        assert res_nonexistent.status_code == 404
    finally:
        db.query(WBSTask).filter(WBSTask.project_id == proj_a).delete()
        db.query(Project).filter(Project.id == proj_a).delete()
        db.commit()
        db.close()


def test_empty_project_execution_summary(auth_headers_tenant_a):
    db = TestingSessionLocal()
    proj_id = f"test-empty-{uuid.uuid4()}"
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Empty Project Without Tasks",
            status="intake",
        )
        db.add(proj)
        db.commit()

        res = client.get(f"/api/execution/summary/{proj_id}", headers=auth_headers_tenant_a)
        assert res.status_code == 200
        summary = res.json()
        assert summary["total_tasks"] == 0
        assert summary["completed_tasks"] == 0
        assert summary["in_progress_tasks"] == 0
        assert summary["blocked_tasks"] == 0
        assert summary["completion_percentage"] == 0.0
        assert summary["total_planned_hours"] == 0.0
        assert summary["total_actual_hours"] == 0.0
        assert summary["active_blockers"] == []
    finally:
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()
