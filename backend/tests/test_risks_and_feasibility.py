import json
import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.project import Project
from app.models.baseline import RequirementBaseline
from app.models.estimation import ProjectEstimate
from app.models.risk import ProjectRisk, FeasibilityAssessment
from app.services.risk.feasibility_service import (
    FeasibilityService,
    calculate_risk_level,
    _evaluate_budget_feasibility,
    _evaluate_schedule_feasibility,
)
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def test_risk_score_and_severity_level_boundaries():
    """
    Verifies deterministic risk score calculation and severity boundaries:
    - low: 1 - 4
    - medium: 5 - 9
    - high: 10 - 15
    - critical: 16 - 25
    """
    # Lower and upper boundary tests
    assert calculate_risk_level(1) == "low"
    assert calculate_risk_level(4) == "low"
    assert calculate_risk_level(5) == "medium"
    assert calculate_risk_level(9) == "medium"
    assert calculate_risk_level(10) == "high"
    assert calculate_risk_level(15) == "high"
    assert calculate_risk_level(16) == "critical"
    assert calculate_risk_level(25) == "critical"

    # Test complete 5x5 matrix
    for likelihood in range(1, 6):
        for impact in range(1, 6):
            score = likelihood * impact
            level = calculate_risk_level(score)
            if score <= 4:
                assert level == "low"
            elif score <= 9:
                assert level == "medium"
            elif score <= 15:
                assert level == "high"
            else:
                assert level == "critical"


def test_budget_feasibility_logic():
    """
    Tests budget feasibility evaluation:
    1. Budget exists and cost <= budget -> feasible
    2. Budget exists and cost marginally exceeds budget (<=15%) -> caution
    3. Budget exists and cost exceeds budget by >15% -> infeasible
    4. Budget is missing/None -> caution with transparent note
    5. Cost estimate is missing -> caution with transparent note
    """
    p = Project(id="p-test", name="Test Proj", tenant_id="tenant-default", target_budget=100000.0)

    # 1. Feasible: cost $80k <= $100k
    est_ok = ProjectEstimate(id="e-1", tenant_id="tenant-default", project_id="p-test", total_cost=80000.0)
    status, score, notes = _evaluate_budget_feasibility(p, est_ok)
    assert status == "feasible"
    assert score == 92.0
    assert "within target budget" in notes
    assert "Remaining buffer: $20,000.00" in notes

    # 2. Caution: cost $110k (10% over budget)
    est_caution = ProjectEstimate(id="e-2", tenant_id="tenant-default", project_id="p-test", total_cost=110000.0)
    status, score, notes = _evaluate_budget_feasibility(p, est_caution)
    assert status == "caution"
    assert status == "caution"
    assert "marginally exceeds target budget" in notes

    # 3. Infeasible: cost $130k (30% over budget)
    est_infeasible = ProjectEstimate(id="e-3", tenant_id="tenant-default", project_id="p-test", total_cost=130000.0)
    status, score, notes = _evaluate_budget_feasibility(p, est_infeasible)
    assert status == "infeasible"
    assert ">15% variance threshold" in notes

    # 4. Missing budget: target_budget = None
    p_nobudget = Project(id="p-nobudget", name="No Budget Proj", tenant_id="tenant-default", target_budget=None)
    status, score, notes = _evaluate_budget_feasibility(p_nobudget, est_ok)
    assert status == "caution"
    assert "No target budget specified" in notes
    assert "Budget feasibility cannot be quantitatively verified" in notes

    # 5. Missing estimate
    status, score, notes = _evaluate_budget_feasibility(p, None)
    assert status == "caution"
    assert "No WBS cost estimate calculated yet" in notes


def test_schedule_feasibility_logic():
    """
    Tests schedule feasibility evaluation:
    1. Target deadline exists and critical path fits -> feasible
    2. Critical path exceeds target deadline by >15% -> infeasible
    3. Missing target deadline -> caution reporting missing input without inventing dates
    4. Missing estimate -> caution reporting missing estimate
    """
    now = datetime.utcnow()
    # Deadline 60 days in future: ~42 working days available
    future_date = (now + timedelta(days=60)).strftime("%Y-%m-%d")
    p = Project(
        id="p-sched",
        name="Sched Proj",
        tenant_id="tenant-default",
        target_deadline=future_date,
        created_at=now,
    )

    # 1. Feasible: critical path 20 working days fits in ~42 days
    est_ok = ProjectEstimate(id="e-s1", tenant_id="tenant-default", project_id="p-sched", estimated_duration_days=20.0)
    status, score, notes = _evaluate_schedule_feasibility(p, est_ok)
    assert status == "feasible"
    assert "fits comfortably within" in notes

    # 2. Infeasible: critical path 80 working days exceeds ~42 days by >15%
    est_over = ProjectEstimate(id="e-s2", tenant_id="tenant-default", project_id="p-sched", estimated_duration_days=80.0)
    status, score, notes = _evaluate_schedule_feasibility(p, est_over)
    assert status == "infeasible"
    assert "exceeds available window" in notes

    # 3. Missing target deadline
    p_nodeadline = Project(id="p-nodeadline", name="No Deadline Proj", tenant_id="tenant-default", target_deadline=None)
    status, score, notes = _evaluate_schedule_feasibility(p_nodeadline, est_ok)
    assert status == "caution"
    assert "No target deadline specified" in notes
    assert "Schedule feasibility cannot be verified against delivery milestones without a target date." in notes

    # 4. Missing estimate
    status, score, notes = _evaluate_schedule_feasibility(p, None)
    assert status == "caution"
    assert "No WBS estimation found" in notes


def test_evaluate_and_get_feasibility_api_lifecycle(auth_headers_tenant_a):
    """
    Verifies full feasibility and risk evaluation lifecycle:
    - POST /api/risks/evaluate/{project_id}
    - Ingests extracted baseline risks from requirements document
    - Generates deterministic systemic risks
    - GET /api/risks/{project_id} returns 7 dimensions and risk register with source tags
    """
    proj_id = f"proj-risk-{uuid.uuid4().hex[:8]}"
    db = TestingSessionLocal()
    try:
        p = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Risk LifeCycle Proj",
            target_budget=50000.0,
            target_deadline="2026-12-31",
            created_by_id="user-mgr-a",
        )
        # Seed active baseline with 1 extracted risk, 1 contradiction, 3 open questions
        req_data = {
            "functional_requirements": [{"id": f"FR-{i}", "title": f"Feature {i}"} for i in range(8)],
            "contradictions": [{"id": "CTR-01", "description": "Contradiction in storage retention"}],
            "missing_information": [
                {"id": "Q-01", "question": "What is the primary auth provider?"},
                {"id": "Q-02", "question": "What is target RTO/RPO?"},
                {"id": "Q-03", "question": "Is SSO required in Phase 1?"},
            ],
            "risks": [
                {
                    "id": "RSK-01",
                    "description": "Third-party identity provider throttling under load.",
                    "severity": "high",
                    "mitigation_hint": "Implement local JWT session caching.",
                    "source_reference": {"location": "Section 4.1", "excerpt": "External IdP integration."},
                }
            ],
        }
        b = RequirementBaseline(
            id=str(uuid.uuid4()),
            tenant_id="tenant-default",
            project_id=proj_id,
            version="1.0",
            draft_id=str(uuid.uuid4()),
            requirements_data_json=json.dumps(req_data),
            is_active=True,
            approved_by_id="user-mgr-a",
            approved_by_name="Manager A",
        )
        est = ProjectEstimate(
            id=str(uuid.uuid4()),
            tenant_id="tenant-default",
            project_id=proj_id,
            total_labor_cost=30000.0,
            contingency_pct=15.0,
            contingency_cost=4500.0,
            total_cost=34500.0,  # <= $50k budget -> feasible
            estimated_duration_days=25.0,  # fits deadline
            critical_path_tasks_json=json.dumps(["TSK-1.1", "TSK-1.2"]),
        )
        db.add_all([p, b, est])
        db.commit()
    finally:
        db.close()

    # 1. POST evaluate
    eval_res = client.post(f"/api/risks/evaluate/{proj_id}", headers=auth_headers_tenant_a)
    assert eval_res.status_code == 200
    data = eval_res.json()

    assert data["overall_status"] in ["feasible", "caution"]
    assert "dimensions" in data
    assert len(data["dimensions"]) == 7
    assert data["dimensions"]["budget"]["status"] == "feasible"
    assert data["dimensions"]["schedule"]["status"] == "feasible"
    assert len(data["limitations"]) == 3

    # Check risk register
    risks = data["risks"]
    assert len(risks) >= 2  # At least extracted RSK-01 + systemic risks
    rsk_codes = [r["risk_code"] for r in risks]
    assert "RSK-01" in rsk_codes
    assert "RSK-SYS-OPS" in rsk_codes

    # Check that extracted risk has AI Suggestion source
    extracted_risk = next(r for r in risks if r["risk_code"] == "RSK-01")
    assert extracted_risk["source"] == "ai_extracted"
    assert "[AI-Extracted" in extracted_risk["supporting_evidence"]
    assert extracted_risk["mitigation_strategy"] == "Implement local JWT session caching."

    # Check that systemic risk has deterministic source
    sys_risk = next(r for r in risks if r["risk_code"] == "RSK-SYS-OPS")
    assert sys_risk["source"] == "deterministic"

    # 2. GET retrieval
    get_res = client.get(f"/api/risks/{proj_id}", headers=auth_headers_tenant_a)
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["overall_score"] == data["overall_score"]
    assert len(get_data["risks"]) == len(risks)


def test_rejection_when_no_approved_baseline(auth_headers_tenant_a):
    """
    Verifies that calling evaluate without an approved baseline returns HTTP 400.
    """
    proj_id = f"proj-nobaseline-{uuid.uuid4().hex[:8]}"
    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="No Baseline Proj", created_by_id="user-mgr-a")
        db.add(p)
        db.commit()
    finally:
        db.close()

    eval_res = client.post(f"/api/risks/evaluate/{proj_id}", headers=auth_headers_tenant_a)
    assert eval_res.status_code == 400
    assert "No approved requirements baseline found" in eval_res.json()["detail"]


def test_update_risk_item_and_manager_review_preservation(auth_headers_tenant_a):
    """
    Verifies that:
    1. Managers can update risk status, likelihood, impact, mitigation strategy, and owner.
    2. Re-evaluating feasibility does NOT overwrite the manager's status update or custom mitigation.
    3. Invalid likelihood/impact (<1 or >5) or invalid status are rejected with HTTP 422.
    """
    proj_id = f"proj-upd-{uuid.uuid4().hex[:8]}"
    db = TestingSessionLocal()
    try:
        p = Project(id=proj_id, tenant_id="tenant-default", name="Update Proj", created_by_id="user-mgr-a")
        b = RequirementBaseline(
            id=str(uuid.uuid4()),
            tenant_id="tenant-default",
            project_id=proj_id,
            version="1.0",
            draft_id=str(uuid.uuid4()),
            requirements_data_json=json.dumps({"functional_requirements": [], "risks": []}),
            is_active=True,
            approved_by_id="user-mgr-a",
            approved_by_name="Manager A",
        )
        db.add_all([p, b])
        db.commit()
    finally:
        db.close()

    # Initial evaluate creates systemic risks
    client.post(f"/api/risks/evaluate/{proj_id}", headers=auth_headers_tenant_a)

    db = TestingSessionLocal()
    try:
        risk = db.query(ProjectRisk).filter(ProjectRisk.project_id == proj_id).first()
        risk_id = risk.id
    finally:
        db.close()

    # 1. Valid update: manager marks as 'mitigated' with custom strategy
    upd_res = client.put(
        f"/api/risks/item/{risk_id}",
        headers=auth_headers_tenant_a,
        json={
            "likelihood": 2,
            "impact": 2,
            "status": "mitigated",
            "mitigation_strategy": "Manager approved circuit breaker strategy.",
            "risk_owner": "Lead Architect",
        },
    )
    assert upd_res.status_code == 200
    upd_data = upd_res.json()
    assert upd_data["status"] == "mitigated"
    assert upd_data["risk_score"] == 4
    assert upd_data["risk_level"] == "low"
    assert upd_data["risk_owner"] == "Lead Architect"

    # 2. Re-evaluate project feasibility: manager's mitigated status must be PRESERVED
    re_eval_res = client.post(f"/api/risks/evaluate/{proj_id}", headers=auth_headers_tenant_a)
    assert re_eval_res.status_code == 200
    refreshed_risks = re_eval_res.json()["risks"]
    preserved = next(r for r in refreshed_risks if r["id"] == risk_id)
    assert preserved["status"] == "mitigated"
    assert preserved["risk_owner"] == "Lead Architect"

    # 3. Invalid inputs: likelihood > 5 -> 422
    fail_lik = client.put(f"/api/risks/item/{risk_id}", headers=auth_headers_tenant_a, json={"likelihood": 6})
    assert fail_lik.status_code == 422

    # Likelihood < 1 -> 422
    fail_neg = client.put(f"/api/risks/item/{risk_id}", headers=auth_headers_tenant_a, json={"likelihood": 0})
    assert fail_neg.status_code == 422

    # Invalid status string -> 422
    fail_stat = client.put(f"/api/risks/item/{risk_id}", headers=auth_headers_tenant_a, json={"status": "invalid_status"})
    assert fail_stat.status_code == 422


def test_project_and_tenant_isolation_for_risks(auth_headers_tenant_a, auth_headers_tenant_b):
    """
    Verifies strict project and tenant isolation:
    1. Tenant B cannot evaluate feasibility for Tenant A's project (HTTP 404).
    2. Tenant B cannot view Tenant A's feasibility or risks (HTTP 404).
    3. Tenant B cannot update Tenant A's risk item (HTTP 404).
    4. Unauthenticated requests are rejected with HTTP 401.
    """
    proj_a = f"proj-iso-{uuid.uuid4().hex[:8]}"
    db = TestingSessionLocal()
    try:
        pa = Project(id=proj_a, tenant_id="tenant-default", name="Tenant A Project", created_by_id="user-mgr-a")
        ba = RequirementBaseline(
            id=str(uuid.uuid4()),
            tenant_id="tenant-default",
            project_id=proj_a,
            version="1.0",
            draft_id=str(uuid.uuid4()),
            requirements_data_json=json.dumps({"functional_requirements": [], "risks": []}),
            is_active=True,
            approved_by_id="user-mgr-a",
            approved_by_name="Manager A",
        )
        ra = ProjectRisk(
            id=str(uuid.uuid4()),
            tenant_id="tenant-default",
            project_id=proj_a,
            risk_code="RSK-ISO",
            title="Tenant A Risk",
            category="security",
            description="Tenant A private risk",
            likelihood=3,
            impact=3,
            risk_score=9,
            risk_level="medium",
        )
        db.add_all([pa, ba, ra])
        db.commit()
        risk_a_id = ra.id
    finally:
        db.close()

    # Tenant B cannot evaluate Tenant A's project -> 404
    eval_b = client.post(f"/api/risks/evaluate/{proj_a}", headers=auth_headers_tenant_b)
    assert eval_b.status_code == 404

    # Tenant B cannot view Tenant A's risks -> 404
    get_b = client.get(f"/api/risks/{proj_a}", headers=auth_headers_tenant_b)
    assert get_b.status_code == 404

    # Tenant B cannot update Tenant A's risk item -> 404
    upd_b = client.put(f"/api/risks/item/{risk_a_id}", headers=auth_headers_tenant_b, json={"status": "mitigated"})
    assert upd_b.status_code == 404

    # Unauthenticated requests -> 401
    assert client.get(f"/api/risks/{proj_a}").status_code == 401
    assert client.post(f"/api/risks/evaluate/{proj_a}").status_code == 401
    assert client.put(f"/api/risks/item/{risk_a_id}", json={"status": "mitigated"}).status_code == 401
