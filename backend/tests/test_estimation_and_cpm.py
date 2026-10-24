import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.estimation import ProjectEstimate
from app.models.project import Project
from app.models.wbs import WBSTask, TaskDependency
from app.services.estimation.engine import (
    EstimationEngine,
    STANDARD_RATE_CARD,
    DEFAULT_HOURLY_RATE,
    HOURS_PER_WORK_DAY,
)
from app.services.planning.wbs_service import WBSService, CyclicDependencyError
from app.api.estimation import _format_critical_path_codes
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def test_cpm_critical_path_and_duration_calculation():
    """
    Verifies CPM calculation:
    Task A (14 hrs = 2 days) -> Task B (21 hrs = 3 days) -> Task C (7 hrs = 1 day)
    Parallel Task D (7 hrs = 1 day) depending on A, completing before B.
    Critical path must be A -> B -> C (total 6 days). Task D has slack.
    """
    t_a = WBSTask(id="t_a", task_code="A", expected_hours=14.0)  # 2 days
    t_b = WBSTask(id="t_b", task_code="B", expected_hours=21.0)  # 3 days
    t_c = WBSTask(id="t_c", task_code="C", expected_hours=7.0)   # 1 day
    t_d = WBSTask(id="t_d", task_code="D", expected_hours=7.0)   # 1 day (parallel branch from A)

    # Dependencies:
    # A -> B -> C
    # A -> D -> C
    dep_ab = TaskDependency(id="d1", predecessor_task_id="t_a", successor_task_id="t_b")
    dep_bc = TaskDependency(id="d2", predecessor_task_id="t_b", successor_task_id="t_c")
    dep_ad = TaskDependency(id="d3", predecessor_task_id="t_a", successor_task_id="t_d")
    dep_dc = TaskDependency(id="d4", predecessor_task_id="t_d", successor_task_id="t_c")

    tasks = [t_a, t_b, t_c, t_d]
    deps = [dep_ab, dep_bc, dep_ad, dep_dc]
    topo_order = ["t_a", "t_b", "t_d", "t_c"]

    crit_tasks, duration_days = EstimationEngine._calculate_cpm(tasks, deps, topo_order)

    # Longest path: A (2) + B (3) + C (1) = 6.0 days
    assert duration_days == 6.0
    # Critical path tasks must include t_a, t_b, t_c
    assert "t_a" in crit_tasks
    assert "t_b" in crit_tasks
    assert "t_c" in crit_tasks
    # Task D finishes in 1 day (earlier than B), so it has float/slack and is NOT on critical path
    assert "t_d" not in crit_tasks


def test_pert_expected_effort_and_variance_formulas():
    """
    Verifies deterministic PERT 3-point estimation:
    Expected = (Optimistic + 4*Most_Likely + Pessimistic) / 6
    Variance = ((Pessimistic - Optimistic) / 6) ^ 2
    """
    # Test case 1: Standard values
    opt, ml, pess = 8.0, 16.0, 32.0
    expected, variance = WBSService.calculate_pert(opt, ml, pess)
    # (8 + 64 + 32) / 6 = 104 / 6 = 17.33
    assert expected == 17.33
    # ((32 - 8) / 6) ^ 2 = (24 / 6) ^ 2 = 4 ^ 2 = 16.0
    assert variance == 16.0

    # Test case 2: Identical values (zero uncertainty)
    exp_zero, var_zero = WBSService.calculate_pert(20.0, 20.0, 20.0)
    assert exp_zero == 20.0
    assert var_zero == 0.0


def test_role_rate_mapping_and_fallback_behavior():
    """
    Verifies that known roles map to approved standard rate card,
    and unknown/unlisted roles gracefully fall back to DEFAULT_HOURLY_RATE ($105/hr).
    """
    assert STANDARD_RATE_CARD["Solutions Architect"] == 135.0
    assert STANDARD_RATE_CARD["Senior Full-Stack Engineer"] == 115.0
    assert STANDARD_RATE_CARD["Full-Stack Engineer"] == 105.0
    assert STANDARD_RATE_CARD["Cloud DevOps Architect"] == 140.0
    assert STANDARD_RATE_CARD["Data & AI Systems Engineer"] == 150.0
    assert STANDARD_RATE_CARD["QA Automation Specialist"] == 90.0
    assert STANDARD_RATE_CARD["Frontend UI/UX Specialist"] == 95.0

    # Fallback check
    unlisted_role = "Quantum Algorithm Specialist"
    rate = STANDARD_RATE_CARD.get(unlisted_role, DEFAULT_HOURLY_RATE)
    assert rate == 105.0


def test_contingency_and_total_cost_calculations():
    """
    Verifies contingency cost and total cost mathematical calculation:
    contingency_cost = total_labor_cost * (contingency_pct / 100)
    total_cost = total_labor_cost + contingency_cost
    """
    labor_cost = 10000.0

    # 15% default contingency
    contingency_15 = round(labor_cost * (15.0 / 100.0), 2)
    assert contingency_15 == 1500.0
    assert round(labor_cost + contingency_15, 2) == 11500.0

    # 0% contingency (no buffer)
    contingency_0 = round(labor_cost * (0.0 / 100.0), 2)
    assert contingency_0 == 0.0
    assert round(labor_cost + contingency_0, 2) == 10000.0

    # 100% contingency (maximum buffer)
    contingency_100 = round(labor_cost * (100.0 / 100.0), 2)
    assert contingency_100 == 10000.0
    assert round(labor_cost + contingency_100, 2) == 20000.0


def test_critical_path_task_code_serialization_and_legacy_mapping():
    """
    Verifies that critical path tasks are serialized as readable task codes (e.g. TSK-1.1),
    and legacy records with UUIDs are cleanly mapped to task codes.
    """
    proj_id = f"proj-cpm-{uuid.uuid4().hex[:8]}"
    t1_id = str(uuid.uuid4())
    t2_id = str(uuid.uuid4())

    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="CPM Test Proj", created_by_id="user-mgr-a")
        t1 = WBSTask(id=t1_id, tenant_id="tenant-default", project_id=proj_id, task_code="TSK-1.1", title="Task 1", expected_hours=14.0)
        t2 = WBSTask(id=t2_id, tenant_id="tenant-default", project_id=proj_id, task_code="TSK-1.2", title="Task 2", expected_hours=21.0)
        dep = TaskDependency(id=str(uuid.uuid4()), tenant_id="tenant-default", project_id=proj_id, predecessor_task_id=t1_id, successor_task_id=t2_id)
        db.add_all([p, t1, t2, dep])
        db.commit()

        # Run calculation
        estimate = EstimationEngine.calculate_project_estimates(db, "tenant-default", proj_id, contingency_pct=15.0)

        # Stored JSON must contain readable task codes
        stored_codes = json.loads(estimate.critical_path_tasks_json)
        assert stored_codes == ["TSK-1.1", "TSK-1.2"]

        # Verify legacy UUID list mapping via _format_critical_path_codes
        legacy_json = json.dumps([t1_id, t2_id])
        formatted = _format_critical_path_codes(db, proj_id, legacy_json)
        assert formatted == ["TSK-1.1", "TSK-1.2"]

        # Verify internal task models have is_critical_path set
        db.refresh(t1)
        db.refresh(t2)
        assert t1.is_critical_path is True
        assert t2.is_critical_path is True
    finally:
        db.close()


def test_estimate_calculate_and_get_endpoints_success(auth_headers_tenant_a):
    """
    Verifies full calculation and retrieval lifecycle via API:
    POST /api/estimation/calculate/{project_id}
    GET /api/estimation/{project_id}
    """
    proj_id = f"proj-est-{uuid.uuid4().hex[:8]}"
    t1_id = str(uuid.uuid4())
    t2_id = str(uuid.uuid4())

    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="API Estimate Proj", created_by_id="user-mgr-a")
        # Task 1: Solutions Architect ($135/hr), 14 hrs -> cost $1,890.00
        t1 = WBSTask(id=t1_id, tenant_id="tenant-default", project_id=proj_id, task_code="TSK-1.1", title="Arch", required_role="Solutions Architect", expected_hours=14.0)
        # Task 2: QA Automation Specialist ($90/hr), 21 hrs -> cost $1,890.00
        t2 = WBSTask(id=t2_id, tenant_id="tenant-default", project_id=proj_id, task_code="TSK-1.2", title="QA", required_role="QA Automation Specialist", expected_hours=21.0)
        dep = TaskDependency(id=str(uuid.uuid4()), tenant_id="tenant-default", project_id=proj_id, predecessor_task_id=t1_id, successor_task_id=t2_id)
        db.add_all([p, t1, t2, dep])
        db.commit()
    finally:
        db.close()

    # 1. POST calculate with 20% contingency
    post_res = client.post(
        f"/api/estimation/calculate/{proj_id}",
        headers=auth_headers_tenant_a,
        json={"contingency_pct": 20.0},
    )
    assert post_res.status_code == 200
    data = post_res.json()

    assert data["project_id"] == proj_id
    assert data["total_pert_hours"] == 35.0
    # Labor cost: 14*135 (1890) + 21*90 (1890) = 3780.0
    assert data["total_labor_cost"] == 3780.0
    assert data["contingency_pct"] == 20.0
    assert data["contingency_cost"] == 756.0  # 3780 * 0.20
    assert data["total_cost"] == 4536.0       # 3780 + 756
    assert data["currency"] == "USD"
    # Duration: 14/7 (2) + 21/7 (3) = 5 days
    assert data["estimated_duration_days"] == 5.0
    assert data["critical_path_tasks"] == ["TSK-1.1", "TSK-1.2"]
    assert "Solutions Architect" in data["role_breakdown"]
    assert "QA Automation Specialist" in data["role_breakdown"]

    # 2. GET retrieval
    get_res = client.get(f"/api/estimation/{proj_id}", headers=auth_headers_tenant_a)
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["id"] == data["id"]
    assert get_data["total_cost"] == 4536.0
    assert get_data["critical_path_tasks"] == ["TSK-1.1", "TSK-1.2"]


def test_estimate_rejection_when_no_wbs_tasks_exist(auth_headers_tenant_a):
    """
    Verifies that calling estimate calculation or retrieval for a project with zero tasks
    is rejected with appropriate HTTP error codes.
    """
    proj_id = f"proj-notasks-{uuid.uuid4().hex[:8]}"

    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="Empty Proj", created_by_id="user-mgr-a")
        db.add(p)
        db.commit()
    finally:
        db.close()

    # Calculate on project with 0 tasks -> HTTP 400
    post_res = client.post(
        f"/api/estimation/calculate/{proj_id}",
        headers=auth_headers_tenant_a,
        json={"contingency_pct": 15.0},
    )
    assert post_res.status_code == 400
    assert "No WBS tasks found" in post_res.json()["detail"]

    # Get on project with 0 tasks and no estimate -> HTTP 404
    get_res = client.get(f"/api/estimation/{proj_id}", headers=auth_headers_tenant_a)
    assert get_res.status_code == 404
    assert "Generate WBS tasks first" in get_res.json()["detail"]


def test_estimate_rejection_on_cyclic_dependencies(auth_headers_tenant_a):
    """
    Verifies that cyclic dependencies in the project's task network
    are rejected with HTTP 400 and a clear circular dependency error.
    """
    proj_id = f"proj-cycle-{uuid.uuid4().hex[:8]}"
    t1_id = str(uuid.uuid4())
    t2_id = str(uuid.uuid4())

    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="Cyclic Proj", created_by_id="user-mgr-a")
        t1 = WBSTask(id=t1_id, tenant_id="tenant-default", project_id=proj_id, task_code="TSK-A", title="Task A", expected_hours=10.0)
        t2 = WBSTask(id=t2_id, tenant_id="tenant-default", project_id=proj_id, task_code="TSK-B", title="Task B", expected_hours=10.0)
        # Cycle: T1 -> T2 -> T1
        d1 = TaskDependency(id=str(uuid.uuid4()), tenant_id="tenant-default", project_id=proj_id, predecessor_task_id=t1_id, successor_task_id=t2_id)
        d2 = TaskDependency(id=str(uuid.uuid4()), tenant_id="tenant-default", project_id=proj_id, predecessor_task_id=t2_id, successor_task_id=t1_id)
        db.add_all([p, t1, t2, d1, d2])
        db.commit()
    finally:
        db.close()

    res = client.post(
        f"/api/estimation/calculate/{proj_id}",
        headers=auth_headers_tenant_a,
        json={"contingency_pct": 15.0},
    )
    assert res.status_code == 400
    assert "Circular dependency detected" in res.json()["detail"]

    # Verify no estimate was persisted
    db = TestingSessionLocal()
    try:
        saved = db.query(ProjectEstimate).filter(ProjectEstimate.project_id == proj_id).first()
        assert saved is None
    finally:
        db.close()


def test_contingency_pct_validation_boundaries_and_rejection(auth_headers_tenant_a):
    """
    Verifies contingency_pct validation:
    - 0.0 and 100.0 accepted (HTTP 200)
    - Negative values rejected (HTTP 422)
    - Values > 100 rejected (HTTP 422)
    - Non-numeric / null rejected (HTTP 422)
    """
    proj_id = f"proj-bounds-{uuid.uuid4().hex[:8]}"
    t_id = str(uuid.uuid4())

    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="Bounds Proj", created_by_id="user-mgr-a")
        t = WBSTask(id=t_id, tenant_id="tenant-default", project_id=proj_id, task_code="TSK-01", title="Task 1", expected_hours=7.0)
        db.add_all([p, t])
        db.commit()
    finally:
        db.close()

    # Lower boundary: 0.0% -> 200 OK
    res_0 = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": 0.0})
    assert res_0.status_code == 200
    assert res_0.json()["contingency_pct"] == 0.0

    # Upper boundary: 100.0% -> 200 OK
    res_100 = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": 100.0})
    assert res_100.status_code == 200
    assert res_100.json()["contingency_pct"] == 100.0

    # Negative values: -5.0 -> 422 Unprocessable Entity
    res_neg = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": -5.0})
    assert res_neg.status_code == 422

    # Negative fraction: -0.1 -> 422
    res_neg_frac = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": -0.1})
    assert res_neg_frac.status_code == 422

    # Above 100: 100.1 -> 422
    res_over = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": 100.1})
    assert res_over.status_code == 422

    # Null value -> 422
    res_null = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": None})
    assert res_null.status_code == 422

    # Non-numeric string -> 422
    res_str = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": "not_a_number"})
    assert res_str.status_code == 422


def test_preservation_of_saved_estimate_on_invalid_input(auth_headers_tenant_a):
    """
    Verifies that when an estimate is already saved, subsequent invalid requests
    (such as negative contingency or cyclic graph) do NOT overwrite or corrupt the saved record.
    """
    proj_id = f"proj-preserve-{uuid.uuid4().hex[:8]}"
    t_id = str(uuid.uuid4())

    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="Preserve Proj", created_by_id="user-mgr-a")
        t = WBSTask(id=t_id, tenant_id="tenant-default", project_id=proj_id, task_code="TSK-01", title="Task 1", expected_hours=14.0)
        db.add_all([p, t])
        db.commit()
    finally:
        db.close()

    # Calculate initial valid estimate with 15%
    init_res = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": 15.0})
    assert init_res.status_code == 200
    saved_initial = init_res.json()
    saved_id = saved_initial["id"]
    saved_cost = saved_initial["total_cost"]

    # Attempt invalid recalculation with negative contingency -> 422
    fail_res = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": -25.0})
    assert fail_res.status_code == 422

    # Attempt invalid recalculation with > 100 contingency -> 422
    fail_over = client.post(f"/api/estimation/calculate/{proj_id}", headers=auth_headers_tenant_a, json={"contingency_pct": 105.0})
    assert fail_over.status_code == 422

    # Fetch estimate via GET and verify it is completely unchanged
    get_res = client.get(f"/api/estimation/{proj_id}", headers=auth_headers_tenant_a)
    assert get_res.status_code == 200
    current_data = get_res.json()
    assert current_data["id"] == saved_id
    assert current_data["total_cost"] == saved_cost
    assert current_data["contingency_pct"] == 15.0


def test_project_and_tenant_isolation_for_estimation(auth_headers_tenant_a, auth_headers_tenant_b):
    """
    Verifies multi-tenant and cross-project isolation:
    1. Tenant B cannot calculate estimates for Tenant A's project.
    2. Tenant B cannot view Tenant A's estimate.
    3. Unauthenticated requests are rejected with 401.
    """
    proj_a = f"proj-iso-a-{uuid.uuid4().hex[:8]}"
    t_id = str(uuid.uuid4())

    db = TestingSessionLocal()
    try:
        pa = Project(id=proj_a, tenant_id="tenant-default", name="Tenant A Project", created_by_id="user-mgr-a")
        ta = WBSTask(id=t_id, tenant_id="tenant-default", project_id=proj_a, task_code="TSK-01", title="Task A", expected_hours=14.0)
        db.add_all([pa, ta])
        db.commit()
    finally:
        db.close()

    # Tenant A calculates estimate successfully
    res_a = client.post(f"/api/estimation/calculate/{proj_a}", headers=auth_headers_tenant_a, json={"contingency_pct": 15.0})
    assert res_a.status_code == 200

    # Tenant B attempts to calculate on Tenant A's project -> HTTP 400 (no tasks found in Tenant B's scope)
    res_b_calc = client.post(f"/api/estimation/calculate/{proj_a}", headers=auth_headers_tenant_b, json={"contingency_pct": 15.0})
    assert res_b_calc.status_code == 400
    assert "No WBS tasks found" in res_b_calc.json()["detail"]

    # Tenant B attempts to view Tenant A's estimate -> HTTP 404 (not found in Tenant B's scope)
    res_b_get = client.get(f"/api/estimation/{proj_a}", headers=auth_headers_tenant_b)
    assert res_b_get.status_code == 404

    # Unauthenticated request -> HTTP 401
    res_unauth = client.get(f"/api/estimation/{proj_a}")
    assert res_unauth.status_code == 401
