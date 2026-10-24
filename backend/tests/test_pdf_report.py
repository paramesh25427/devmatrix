import json
import os
import uuid
import pypdf
from pypdf import PdfReader
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.project import Project
from app.models.baseline import RequirementBaseline
from app.models.wbs import WBSTask, TaskDependency
from app.models.estimation import ProjectEstimate
from app.models.risk import ProjectRisk, FeasibilityAssessment
from app.models.workforce import TeamRecommendation
from app.models.execution import TaskUpdateRecord
from app.models.report import ProjectReport
from app.services.reports.pdf_service import ReportGeneratorService
from tests.conftest import TestingSessionLocal


client = TestClient(app)


def test_pdf_report_generation_and_text_selectability():
    """Verifies that PDF report is generated with ReportLab, has %PDF- signature, and contains selectable text."""
    db = TestingSessionLocal()
    proj_id = f"test-pdf-{uuid.uuid4()}"
    try:
        project = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Forensic PDF Test Project",
            status="intake",
        )
        db.add(project)
        db.commit()

        report = ReportGeneratorService.generate_delivery_report(
            db=db,
            tenant_id="tenant-default",
            project_id=project.id,
            generated_by_name="Lead Auditor",
        )

        assert report is not None
        assert os.path.exists(report.file_path)
        assert report.file_size_bytes > 0

        # 1. Verify %PDF- signature
        with open(report.file_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"

        # 2. Verify pypdf can read the PDF and extract selectable text
        reader = pypdf.PdfReader(report.file_path)
        assert len(reader.pages) >= 1
        full_text = " ".join(page.extract_text() for page in reader.pages)
        assert "DEVMATRIX AI" in full_text
        assert "Forensic PDF Test Project" in full_text
        assert "Engineering Assumptions" in full_text
    finally:
        db.query(ProjectReport).filter(ProjectReport.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_report_inclusion_of_all_available_modules(auth_headers_tenant_a):
    """
    Verifies that the generated PDF report contains data from:
    1. Project metadata
    2. Requirements baseline (v1)
    3. WBS tasks and dependencies
    4. PERT & CPM estimate
    5. Feasibility & Risk register
    6. Workforce recommendations
    7. Execution progress & actual hours
    8. Assumptions & timestamp
    """
    db = TestingSessionLocal()
    proj_id = f"test-full-{uuid.uuid4()}"
    t1_id = f"t1-{uuid.uuid4()}"
    t2_id = f"t2-{uuid.uuid4()}"
    try:
        # 1. Project
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Comprehensive Enterprise Banking Portal",
            description="Core digital banking and real-time ledger microservices migration.",
            status="in_progress",
        )
        db.add(proj)

        # 2. Baseline
        b_data = {
            "functional_requirements": [
                {
                    "id": "FR-AUTH-01",
                    "category": "Authentication",
                    "title": "OAuth2 with Biometric MFA Token",
                    "priority": "critical",
                }
            ]
        }
        baseline = RequirementBaseline(
            id=f"base-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            draft_id=f"draft-{uuid.uuid4()}",
            version=1,
            requirements_data_json=json.dumps(b_data),
            approved_by_id="user-mgr-a",
            approved_by_name="Senior Delivery Director",
            is_active=True,
        )
        db.add(baseline)

        # 3. WBS Tasks & Dependency
        t1 = WBSTask(
            id=t1_id,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-101",
            title="Design Zero-Trust Network Topology",
            required_role="Security Architect",
            status="completed",
            progress_percentage=100.0,
            expected_hours=24.0,
            actual_hours=22.5,
            is_critical_path=True,
            order_index=0,
        )
        t2 = WBSTask(
            id=t2_id,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-102",
            title="Implement Token Exchange Gateway",
            required_role="Backend Engineer",
            status="in_progress",
            progress_percentage=50.0,
            expected_hours=40.0,
            actual_hours=18.0,
            is_critical_path=True,
            order_index=1,
        )
        dep = TaskDependency(
            id=f"dep-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            predecessor_task_id=t1_id,
            successor_task_id=t2_id,
            dependency_type="finish_to_start",
        )
        db.add_all([t1, t2, dep])

        # 4. Estimate
        estimate = ProjectEstimate(
            id=f"est-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            baseline_version=1,
            total_pert_hours=64.0,
            estimated_duration_days=8.0,
            total_labor_cost=7680.0,
            contingency_pct=15.0,
            contingency_cost=1152.0,
            total_cost=8832.0,
            rate_card_version="2026-Q1-Standard",
            critical_path_tasks_json=json.dumps(["TSK-101", "TSK-102"]),
        )
        db.add(estimate)

        # 5. Risks & Feasibility
        risk = ProjectRisk(
            id=f"risk-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            risk_code="RSK-SEC-01",
            title="Hardware Security Module Latency",
            category="technical",
            description="HSM provider response SLA is 120ms during peak load.",
            likelihood=3,
            impact=4,
            risk_score=12,
            risk_level="high",
            supporting_evidence="HSM provider response SLA is 120ms during peak load.",
            mitigation_strategy="Implement read-through caching for non-repudiation tokens.",
        )
        feasibility = FeasibilityAssessment(
            id=f"feas-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            overall_status="feasible",
            overall_score=88.0,
            dimensions_json=json.dumps({
                "budget": {"status": "feasible", "score": 90.0, "notes": "Budget within target."},
                "schedule": {"status": "feasible", "score": 85.0, "notes": "Schedule achievable."},
            }),
            summary="Schedule and budget feasible with 15% contingency reserve.",
        )
        db.add_all([risk, feasibility])

        # 6. Workforce
        rec = TeamRecommendation(
            id=f"rec-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            task_id=t1_id,
            role_needed="Security Architect",
            candidate_id="user-sec-1",
            candidate_name="Kavita Rao",
            match_score=92.5,
            skill_score=95.0,
            availability_score=90.0,
            experience_score=90.0,
            workload_score=95.0,
            rationale="10+ years enterprise cybersecurity and Kubernetes service mesh certification.",
            manager_status="approved",
        )
        db.add(rec)

        # 7. Execution Update Record
        update_rec = TaskUpdateRecord(
            id=f"upd-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            task_id=t1_id,
            user_id="user-mgr-a",
            user_name="manager@devmatrix.local",
            hours_logged=10.0,
            previous_status="in_progress",
            new_status="completed",
            progress_percentage=100.0,
            progress_notes="Completed security audit review and sign-off",
            blocker_flag="false",
        )
        db.add(update_rec)
        db.commit()

        # Generate report via API
        res = client.post(f"/api/reports/generate/{proj_id}", headers=auth_headers_tenant_a)
        assert res.status_code == 201, res.text
        data = res.json()
        report_id = data["id"]

        report_db = db.query(ProjectReport).filter(ProjectReport.id == report_id).first()
        assert report_db is not None
        assert os.path.exists(report_db.file_path)

        # Extract text and verify all 8 domains are represented
        reader = pypdf.PdfReader(report_db.file_path)
        full_text = " ".join(page.extract_text() for page in reader.pages)

        # Domain 1: Project
        assert "Comprehensive Enterprise Banking Portal" in full_text
        # Domain 2: Baseline
        assert "FR-AUTH-01" in full_text
        assert "OAuth2 with Biometric MFA Token" in full_text
        # Domain 3: WBS & Dependency
        assert "TSK-101" in full_text
        assert "TSK-102" in full_text
        assert "Design Zero-Trust Network Topology" in full_text
        # Domain 4: Estimate
        assert "64.0" in full_text
        assert "8,832.00" in full_text
        # Domain 5: Risks & Feasibility
        assert "RSK-SEC-01" in full_text
        assert "FEASIBLE" in full_text
        # Domain 6: Workforce
        assert "Kavita Rao" in full_text
        assert "92%" in full_text or "92.5%" in full_text
        # Domain 7: Execution
        assert "TSK-101" in full_text
        assert "22.5" in full_text or "40.5" in full_text
        # Domain 8: Assumptions & Forensic Checksum
        assert "Engineering Assumptions" in full_text
        assert "DevMatrix AI v1.0.0" in full_text
    finally:
        db.query(TaskUpdateRecord).filter(TaskUpdateRecord.project_id == proj_id).delete()
        db.query(TeamRecommendation).filter(TeamRecommendation.project_id == proj_id).delete()
        db.query(FeasibilityAssessment).filter(FeasibilityAssessment.project_id == proj_id).delete()
        db.query(ProjectRisk).filter(ProjectRisk.project_id == proj_id).delete()
        db.query(ProjectEstimate).filter(ProjectEstimate.project_id == proj_id).delete()
        db.query(TaskDependency).filter(TaskDependency.project_id == proj_id).delete()
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(RequirementBaseline).filter(RequirementBaseline.project_id == proj_id).delete()
        db.query(ProjectReport).filter(ProjectReport.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_graceful_handling_of_missing_optional_sections(auth_headers_tenant_a):
    """Verifies that project with zero baseline, tasks, or estimates generates PDF gracefully without error."""
    db = TestingSessionLocal()
    proj_id = f"test-bare-{uuid.uuid4()}"
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Bare Minimal Project",
            status="intake",
        )
        db.add(proj)
        db.commit()

        res = client.post(f"/api/reports/generate/{proj_id}", headers=auth_headers_tenant_a)
        assert res.status_code == 201
        report = db.query(ProjectReport).filter(ProjectReport.id == res.json()["id"]).first()
        assert report is not None
        assert os.path.exists(report.file_path)

        reader = pypdf.PdfReader(report.file_path)
        full_text = " ".join(page.extract_text() for page in reader.pages)
        assert "Bare Minimal Project" in full_text
        assert "No approved requirements baseline found" in full_text
        assert "No WBS tasks generated" in full_text
    finally:
        db.query(ProjectReport).filter(ProjectReport.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_no_mutation_of_existing_project_data(auth_headers_tenant_a):
    """Verifies that PDF report generation is strictly read-only and does NOT alter or mutate project data."""
    db = TestingSessionLocal()
    proj_id = f"test-nomutate-{uuid.uuid4()}"
    t_id = f"task-nomutate-{uuid.uuid4()}"
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Data Immutability Test Project",
            status="intake",
        )
        task = WBSTask(
            id=t_id,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-FIXED",
            title="Fixed Immutable Task",
            expected_hours=14.0,
            actual_hours=3.5,
            status="in_progress",
            progress_percentage=25.0,
        )
        db.add(proj)
        db.add(task)
        db.commit()

        # Capture pre-generation state
        task_before = db.query(WBSTask).filter(WBSTask.id == t_id).first()
        status_before = task_before.status
        progress_before = task_before.progress_percentage
        hours_before = task_before.actual_hours

        # Generate report
        res = client.post(f"/api/reports/generate/{proj_id}", headers=auth_headers_tenant_a)
        assert res.status_code == 201

        # Verify post-generation state
        db.expire_all()
        task_after = db.query(WBSTask).filter(WBSTask.id == t_id).first()
        assert task_after.status == status_before
        assert task_after.progress_percentage == progress_before
        assert task_after.actual_hours == hours_before
    finally:
        db.query(ProjectReport).filter(ProjectReport.project_id == proj_id).delete()
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_reports_api_download_and_tenant_isolation(auth_headers_tenant_a, token_manager_b):
    """
    Verifies:
    1. Report generation, listing, and download work over API.
    2. Download returns media_type='application/pdf' and safe filename.
    3. Other tenant is rejected with HTTP 404 for generate, list, and download.
    4. Unauthenticated download fails with HTTP 401.
    """
    db = TestingSessionLocal()
    proj_id = f"test-tenant-report-{uuid.uuid4()}"
    other_tenant_auth = {"Authorization": f"Bearer {token_manager_b}"}
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Tenant Isolation Report Project",
            status="intake",
        )
        db.add(proj)
        db.commit()

        # Generate report for tenant A
        gen_res = client.post(f"/api/reports/generate/{proj_id}", headers=auth_headers_tenant_a)
        assert gen_res.status_code == 201
        report_id = gen_res.json()["id"]

        # List reports for tenant A
        list_res = client.get(f"/api/reports/{proj_id}", headers=auth_headers_tenant_a)
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # Download report for tenant A
        dl_res = client.get(f"/api/reports/{report_id}/download", headers=auth_headers_tenant_a)
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/pdf"
        assert dl_res.content[:5] == b"%PDF-"
        assert "filename=" in dl_res.headers.get("content-disposition", "")

        # Cross-tenant generate rejected with 404
        cross_gen = client.post(f"/api/reports/generate/{proj_id}", headers=other_tenant_auth)
        assert cross_gen.status_code == 404

        # Cross-tenant list rejected with 404
        cross_list = client.get(f"/api/reports/{proj_id}", headers=other_tenant_auth)
        assert cross_list.status_code == 404

        # Cross-tenant download rejected with 404
        cross_dl = client.get(f"/api/reports/{report_id}/download", headers=other_tenant_auth)
        assert cross_dl.status_code == 404

        # Unauthenticated download rejected with 401
        unauth_dl = client.get(f"/api/reports/{report_id}/download")
        assert unauth_dl.status_code == 401
    finally:
        db.query(ProjectReport).filter(ProjectReport.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_long_text_wrapping_no_truncation(auth_headers_tenant_a):
    """
    Regression test verifying that long task titles, required roles, risk titles,
    mitigation strategies, candidate rationales, and progress notes are wrapped
    without truncation in the generated PDF.
    """
    db = TestingSessionLocal()
    proj_id = f"test-longtext-{uuid.uuid4()}"
    t1_id = f"t1-{uuid.uuid4()}"
    long_task_title = "Comprehensive Zero-Trust Infrastructure and Microservices Ingress Controller Deployment Architecture"
    long_role = "Principal Distributed Systems Cloud Security Engineer"
    long_risk_title = "Hardware Security Module Cluster Geographic Failover Latency Spike and Session Drop Risk"
    long_mitigation = "Deploy multi-region HSM read-replicas with cached token verification and automated BGP route failover mechanisms."
    long_rationale = "Over 12 years of hands-on experience designing Kubernetes service meshes, multi-cluster ingress routing, and strict zero-trust security postures."
    long_notes = "Successfully finalized cryptographic key rotation protocols, verified audit logs, and signed off with delivery assurance committee."

    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Extended Forensic Scope Project",
            status="in_progress",
        )
        db.add(proj)

        t1 = WBSTask(
            id=t1_id,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-WRAP-01",
            title=long_task_title,
            required_role=long_role,
            status="completed",
            progress_percentage=100.0,
            expected_hours=40.0,
            actual_hours=38.0,
            is_critical_path=True,
            order_index=0,
        )
        db.add(t1)

        estimate = ProjectEstimate(
            id=f"est-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            baseline_version=1,
            total_pert_hours=40.0,
            estimated_duration_days=5.0,
            total_labor_cost=4000.0,
            contingency_pct=10.0,
            contingency_cost=400.0,
            total_cost=4400.0,
            rate_card_version="2026-Q1-Standard",
            critical_path_tasks_json=json.dumps(["TSK-WRAP-01"]),
        )
        db.add(estimate)

        risk = ProjectRisk(
            id=f"risk-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            risk_code="RSK-WRAP-01",
            title=long_risk_title,
            category="security",
            description=long_risk_title,
            likelihood=3,
            impact=4,
            risk_score=12,
            risk_level="high",
            supporting_evidence="Peak telemetry confirms 180ms p99 spike during failover tests.",
            mitigation_strategy=long_mitigation,
        )
        db.add(risk)

        rec = TeamRecommendation(
            id=f"rec-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            task_id=t1_id,
            role_needed=long_role,
            candidate_id="cand-wrap-1",
            candidate_name="Dr. Alexander Hamilton",
            match_score=94.0,
            skill_score=95.0,
            availability_score=90.0,
            experience_score=98.0,
            workload_score=90.0,
            rationale=long_rationale,
            manager_status="approved",
        )
        db.add(rec)

        upd = TaskUpdateRecord(
            id=f"upd-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            task_id=t1_id,
            user_id="user-mgr-a",
            user_name="Lead Assessor",
            hours_logged=8.0,
            previous_status="in_progress",
            new_status="completed",
            progress_percentage=100.0,
            progress_notes=long_notes,
            blocker_flag="false",
        )
        db.add(upd)
        db.commit()

        # Generate report
        res = client.post(f"/api/reports/generate/{proj_id}", headers=auth_headers_tenant_a)
        assert res.status_code == 201
        report_id = res.json()["id"]

        report_db = db.query(ProjectReport).filter(ProjectReport.id == report_id).first()
        assert report_db is not None
        assert os.path.exists(report_db.file_path)

        with open(report_db.file_path, "rb") as f:
            reader = PdfReader(f)
            raw_text = " ".join([page.extract_text() for page in reader.pages])
            full_text = " ".join(raw_text.split())

        # Verify that all long texts are present in full without substring slicing
        assert "Ingress Controller Deployment Architecture" in full_text
        assert "Cloud Security Engineer" in full_text
        assert "Failover Latency Spike and Session Drop Risk" in full_text
        assert "BGP route failover mechanisms" in full_text
        assert "Kubernetes service meshes" in full_text
        assert "delivery assurance committee" in full_text

    finally:
        db.query(ProjectReport).filter(ProjectReport.project_id == proj_id).delete()
        db.query(TaskUpdateRecord).filter(TaskUpdateRecord.project_id == proj_id).delete()
        db.query(TeamRecommendation).filter(TeamRecommendation.project_id == proj_id).delete()
        db.query(ProjectRisk).filter(ProjectRisk.project_id == proj_id).delete()
        db.query(ProjectEstimate).filter(ProjectEstimate.project_id == proj_id).delete()
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_critical_path_uuid_resolution_to_task_codes(auth_headers_tenant_a):
    """
    Regression test verifying that raw UUIDs in critical path records are
    deterministically resolved to human-readable task codes (e.g. TSK-CP-01 -> TSK-CP-02)
    and raw UUIDs are not displayed in the critical path sequence.
    """
    db = TestingSessionLocal()
    proj_id = f"test-cp-res-{uuid.uuid4()}"
    t1_uuid = str(uuid.uuid4())
    t2_uuid = str(uuid.uuid4())
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Critical Path Code Resolution Project",
            status="in_progress",
        )
        db.add(proj)

        t1 = WBSTask(
            id=t1_uuid,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-CP-01",
            title="Database Sharding Architecture",
            required_role="Database Architect",
            status="completed",
            expected_hours=20.0,
            actual_hours=20.0,
            is_critical_path=True,
            order_index=0,
        )
        t2 = WBSTask(
            id=t2_uuid,
            tenant_id="tenant-default",
            project_id=proj_id,
            task_code="TSK-CP-02",
            title="Cross-Partition Consensus Engine",
            required_role="Backend Specialist",
            status="in_progress",
            expected_hours=30.0,
            actual_hours=15.0,
            is_critical_path=True,
            order_index=1,
        )
        db.add_all([t1, t2])

        # Estimate contains raw UUIDs in critical_path_tasks_json
        estimate = ProjectEstimate(
            id=f"est-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            baseline_version=1,
            total_pert_hours=50.0,
            estimated_duration_days=6.25,
            total_labor_cost=5000.0,
            contingency_pct=10.0,
            contingency_cost=500.0,
            total_cost=5500.0,
            rate_card_version="2026-Q1-Standard",
            critical_path_tasks_json=json.dumps([t1_uuid, t2_uuid]),
        )
        db.add(estimate)
        db.commit()

        res = client.post(f"/api/reports/generate/{proj_id}", headers=auth_headers_tenant_a)
        assert res.status_code == 201
        report_id = res.json()["id"]

        report_db = db.query(ProjectReport).filter(ProjectReport.id == report_id).first()
        with open(report_db.file_path, "rb") as f:
            reader = PdfReader(f)
            full_text = " ".join([page.extract_text() for page in reader.pages])

        # Assert human-readable codes appear in critical path sequence
        assert "TSK-CP-01" in full_text
        assert "TSK-CP-02" in full_text
        # Assert raw UUID strings do NOT appear in the critical path sequence text
        assert f"{t1_uuid} -> {t2_uuid}" not in full_text
        assert f"{t1_uuid} &rarr; {t2_uuid}" not in full_text

    finally:
        db.query(ProjectReport).filter(ProjectReport.project_id == proj_id).delete()
        db.query(ProjectEstimate).filter(ProjectEstimate.project_id == proj_id).delete()
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()


def test_multi_page_tables_and_page_numbering(auth_headers_tenant_a):
    """
    Regression test verifying multi-page table handling, repeated table headers,
    and two-pass page numbering ('Page X of Y').
    """
    db = TestingSessionLocal()
    proj_id = f"test-multipage-{uuid.uuid4()}"
    try:
        proj = Project(
            id=proj_id,
            tenant_id="tenant-default",
            name="Multi-Page Enterprise Infrastructure Assessment",
            status="in_progress",
        )
        db.add(proj)

        # Create 16 tasks and dependencies to span across multiple pages
        task_ids = []
        for i in range(16):
            tid = f"task-mp-{i}-{uuid.uuid4()}"
            t = WBSTask(
                id=tid,
                tenant_id="tenant-default",
                project_id=proj_id,
                task_code=f"TSK-MP-{i+1:02d}",
                title=f"Infrastructure Scaling Subsystem Component Module {i+1}",
                required_role="Systems Engineer",
                status="in_progress" if i % 2 == 0 else "completed",
                expected_hours=16.0,
                actual_hours=8.0,
                is_critical_path=(i < 4),
                order_index=i,
            )
            db.add(t)
            task_ids.append(tid)

        for i in range(len(task_ids) - 1):
            dep = TaskDependency(
                id=f"dep-mp-{i}-{uuid.uuid4()}",
                tenant_id="tenant-default",
                project_id=proj_id,
                predecessor_task_id=task_ids[i],
                successor_task_id=task_ids[i+1],
                dependency_type="finish_to_start",
            )
            db.add(dep)

        estimate = ProjectEstimate(
            id=f"est-{uuid.uuid4()}",
            tenant_id="tenant-default",
            project_id=proj_id,
            baseline_version=1,
            total_pert_hours=256.0,
            estimated_duration_days=32.0,
            total_labor_cost=25600.0,
            contingency_pct=15.0,
            contingency_cost=3840.0,
            total_cost=29440.0,
            rate_card_version="2026-Q1-Standard",
            critical_path_tasks_json=json.dumps(task_ids[:4]),
        )
        db.add(estimate)
        db.commit()

        res = client.post(f"/api/reports/generate/{proj_id}", headers=auth_headers_tenant_a)
        assert res.status_code == 201
        report_id = res.json()["id"]

        report_db = db.query(ProjectReport).filter(ProjectReport.id == report_id).first()
        with open(report_db.file_path, "rb") as f:
            reader = PdfReader(f)
            num_pages = len(reader.pages)
            assert num_pages >= 2, f"Expected multiple pages, got {num_pages}"

            p1_text = reader.pages[0].extract_text()
            assert f"Page 1 of {num_pages}" in p1_text

            p2_text = reader.pages[1].extract_text()
            assert f"Page 2 of {num_pages}" in p2_text
            assert "DEVMATRIX AI | PROJECT FORENSIC & EXECUTIVE DELIVERY REPORT" in p2_text

    finally:
        db.query(ProjectReport).filter(ProjectReport.project_id == proj_id).delete()
        db.query(TaskDependency).filter(TaskDependency.project_id == proj_id).delete()
        db.query(ProjectEstimate).filter(ProjectEstimate.project_id == proj_id).delete()
        db.query(WBSTask).filter(WBSTask.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()

