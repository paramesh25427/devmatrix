import pytest
from app.services.planning.wbs_service import WBSService, CyclicDependencyError
from app.models.wbs import WBSTask, TaskDependency


def test_pert_three_point_estimation_formula():
    """
    Verifies PERT formulas:
    Expected = (Optimistic + 4*Most_Likely + Pessimistic) / 6
    Variance = ((Pessimistic - Optimistic) / 6) ^ 2
    """
    opt = 10.0
    ml = 20.0
    pess = 40.0

    expected, variance = WBSService.calculate_pert(opt, ml, pess)

    # (10 + 4*20 + 40) / 6 = 130 / 6 = 21.67
    assert expected == 21.67
    # ((40 - 10) / 6) ^ 2 = (30 / 6) ^ 2 = 5 ^ 2 = 25.0
    assert variance == 25.0


def test_wbs_dag_topological_sort_valid():
    """Verifies that a valid acyclic dependency graph resolves in topological order."""
    t1 = WBSTask(id="t1", task_code="TSK-01")
    t2 = WBSTask(id="t2", task_code="TSK-02")
    t3 = WBSTask(id="t3", task_code="TSK-03")

    # t1 -> t2 -> t3
    dep1 = TaskDependency(id="d1", predecessor_task_id="t1", successor_task_id="t2")
    dep2 = TaskDependency(id="d2", predecessor_task_id="t2", successor_task_id="t3")

    topo_order = WBSService.validate_dependencies([t1, t2, t3], [dep1, dep2])
    assert topo_order == ["t1", "t2", "t3"]


def test_wbs_cycle_detection_rejects_circular_dependencies():
    """
    Verifies that cyclic dependencies (e.g., T1 -> T2 -> T3 -> T1)
    are explicitly detected and rejected with CyclicDependencyError.
    """
    t1 = WBSTask(id="t1", task_code="TSK-01")
    t2 = WBSTask(id="t2", task_code="TSK-02")
    t3 = WBSTask(id="t3", task_code="TSK-03")

    # Cycle: t1 -> t2 -> t3 -> t1
    dep1 = TaskDependency(id="d1", predecessor_task_id="t1", successor_task_id="t2")
    dep2 = TaskDependency(id="d2", predecessor_task_id="t2", successor_task_id="t3")
    dep3 = TaskDependency(id="d3", predecessor_task_id="t3", successor_task_id="t1")

    with pytest.raises(CyclicDependencyError) as exc_info:
        WBSService.validate_dependencies([t1, t2, t3], [dep1, dep2, dep3])

    err_msg = str(exc_info.value)
    assert "Circular dependency detected" in err_msg


def test_wbs_self_dependency_rejected():
    """Tasks cannot depend on themselves."""
    t1 = WBSTask(id="t1", task_code="TSK-01")
    self_dep = TaskDependency(id="d1", predecessor_task_id="t1", successor_task_id="t1")

    with pytest.raises(CyclicDependencyError):
        WBSService.validate_dependencies([t1], [self_dep])


# =========================================================================
# WBS Approval Guard Integration Tests
# =========================================================================

import json
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.models.baseline import RequirementBaseline
from app.models.requirement import RequirementDraft
from app.models.project import Project
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def test_wbs_generate_missing_baseline_rejected(auth_headers_tenant_a):
    """
    Verify that calling generate_wbs for a project with no approved baseline
    returns HTTP 400 and creates zero tasks.
    """
    proj_id = f"proj-nobaseline-{uuid.uuid4().hex[:8]}"

    res = client.post(f"/api/wbs/generate/{proj_id}", headers=auth_headers_tenant_a)
    assert res.status_code == 400
    assert "No approved requirements baseline found" in res.json()["detail"]

    # Verify zero tasks created in database
    db = TestingSessionLocal()
    try:
        tasks = db.query(WBSTask).filter(WBSTask.project_id == proj_id).all()
        assert len(tasks) == 0
    finally:
        db.close()


def test_wbs_generate_revision_requested_draft_rejected(auth_headers_tenant_a):
    """
    Verify that a draft in revision_requested / pending_review status without an
    approved RequirementBaseline cannot be used to generate WBS tasks.
    """
    proj_id = f"proj-revdraft-{uuid.uuid4().hex[:8]}"
    draft_id = str(uuid.uuid4())

    db = TestingSessionLocal()
    try:
        # Create project
        p = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Atlas Draft Project",
            status="intake",
            created_by_id="user-mgr-a",
        )
        db.add(p)

        # Create draft with status 'revision_requested' and no baseline
        draft = RequirementDraft(
            id=draft_id,
            tenant_id="tenant-default",
            project_id=proj_id,
            document_id=f"doc-{uuid.uuid4().hex[:8]}",
            document_name="atlas_spec.pdf",
            provider_used="gemini",
            model_used="gemini-3.5-flash",
            status="draft_ready",
            review_status="revision_requested",
            is_approved_baseline=False,
            manager_notes="Please clarify latency constraints and multi-region SLAs.",
        )
        db.add(draft)
        db.commit()
    finally:
        db.close()

    # Attempt to generate WBS
    res = client.post(f"/api/wbs/generate/{proj_id}", headers=auth_headers_tenant_a)
    assert res.status_code == 400
    assert "No approved requirements baseline found" in res.json()["detail"]

    # Confirm 0 tasks created
    db = TestingSessionLocal()
    try:
        tasks = db.query(WBSTask).filter(WBSTask.project_id == proj_id).all()
        assert len(tasks) == 0
    finally:
        db.close()


def test_wbs_generate_cross_project_and_tenant_isolation(auth_headers_tenant_a, auth_headers_tenant_b):
    """
    Verify cross-project and cross-tenant isolation:
    1. Tenant B cannot generate WBS using Tenant A's baseline.
    2. Tenant A cannot use requirements from another project without its own baseline.
    """
    proj_a = f"proj-tenant-a-{uuid.uuid4().hex[:8]}"
    proj_b = f"proj-tenant-b-{uuid.uuid4().hex[:8]}"

    db = TestingSessionLocal()
    try:
        # Create Project A in Tenant A with active approved baseline
        pa = Project(id=proj_a, tenant_id="tenant-default", name="Tenant A Project", status="planning", created_by_id="user-mgr-a")
        bl_a = RequirementBaseline(
            id=str(uuid.uuid4()),
            tenant_id="tenant-default",
            project_id=proj_a,
            version=1,
            draft_id=str(uuid.uuid4()),
            approved_by_id="user-mgr-a",
            approved_by_name="manager@devmatrix.local",
            requirements_data_json=json.dumps({"functional_requirements": [{"id": "FR-01", "title": "Auth"}]}),
            is_active=True,
        )
        db.add(pa)
        db.add(bl_a)

        # Create Project B in Tenant B without baseline
        pb = Project(id=proj_b, tenant_id="tenant-beta", name="Tenant B Project", status="intake", created_by_id="user-mgr-b")
        db.add(pb)
        db.commit()
    finally:
        db.close()

    # Test 1: Tenant B attempts to generate WBS on Tenant A's project
    res_cross_tenant = client.post(f"/api/wbs/generate/{proj_a}", headers=auth_headers_tenant_b)
    assert res_cross_tenant.status_code == 400
    assert "No approved requirements baseline found" in res_cross_tenant.json()["detail"]

    # Test 2: Tenant A attempts to generate WBS on Project B (which has no baseline)
    res_cross_proj = client.post(f"/api/wbs/generate/{proj_b}", headers=auth_headers_tenant_a)
    assert res_cross_proj.status_code == 400
    assert "No approved requirements baseline found" in res_cross_proj.json()["detail"]

    # Verify no tasks created for either project through unauthorized requests
    db = TestingSessionLocal()
    try:
        tasks_b = db.query(WBSTask).filter(WBSTask.project_id == proj_b).all()
        assert len(tasks_b) == 0
    finally:
        db.close()


def test_wbs_generate_approved_baseline_success(auth_headers_tenant_a):
    """
    Verify that when an approved, active RequirementBaseline exists for the project,
    WBS generation succeeds and persists candidate tasks with PERT calculations.
    """
    proj_id = f"proj-approved-{uuid.uuid4().hex[:8]}"

    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="Approved Planning Project", status="planning", created_by_id="user-mgr-a")
        bl = RequirementBaseline(
            id=str(uuid.uuid4()),
            tenant_id="tenant-default",
            project_id=proj_id,
            version=1,
            draft_id=str(uuid.uuid4()),
            approved_by_id="user-mgr-a",
            approved_by_name="manager@devmatrix.local",
            requirements_data_json=json.dumps({
                "functional_requirements": [
                    {"id": "FR-01", "title": "Document Parsing"},
                    {"id": "FR-02", "title": "AI Fallback Router"},
                ]
            }),
            is_active=True,
        )
        db.add(p)
        db.add(bl)
        db.commit()
    finally:
        db.close()

    # Call generate WBS
    res = client.post(f"/api/wbs/generate/{proj_id}", headers=auth_headers_tenant_a)
    assert res.status_code == 200
    tasks_data = res.json()
    assert isinstance(tasks_data, list)
    assert len(tasks_data) > 0

    # Verify task structure
    first_task = tasks_data[0]
    assert "id" in first_task
    assert "task_code" in first_task
    assert first_task["project_id"] == proj_id
    assert first_task["expected_hours"] > 0
    assert first_task["variance_hours"] >= 0

    # Verify tasks persisted in database
    db = TestingSessionLocal()
    try:
        db_tasks = db.query(WBSTask).filter(WBSTask.project_id == proj_id).all()
        assert len(db_tasks) == len(tasks_data)
    finally:
        db.close()

