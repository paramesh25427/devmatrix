import sys
import os
import json
from datetime import datetime

# Ensure backend root is on sys.path
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project
from app.models.document import Document
from app.models.workforce import WorkforceMember
from app.models.audit import AuditLog


def seed_demo_data():
    """Seeds a development-only demonstration tenant, users for all 4 roles, workforce profiles, and projects."""
    print("[*] Seeding DevMatrix AI development demonstration environment...")
    db = SessionLocal()
    try:
        # 1. Tenant
        tenant = db.query(Tenant).filter(Tenant.id == "tenant-default").first()
        if not tenant:
            tenant = Tenant(
                id="tenant-default",
                name="Acme Enterprise Delivery",
                slug="acme-enterprise",
                currency="USD",
                default_contingency_pct="15.0",
                retention_days="365",
            )
            db.add(tenant)
            db.flush()
            print("  [+] Created default tenant: Acme Enterprise Delivery")

        # 2. Users for all 4 roles
        demo_password_hash = hash_password("DevMatrix2026!")
        roles_data = [
            ("admin@devmatrix.local", "Sarah Connor (Admin)", "tenant_admin", "usr-admin-01"),
            ("manager@devmatrix.local", "Alex Morgan (Delivery Manager)", "delivery_manager", "usr-manager-01"),
            ("lead@devmatrix.local", "David Chen (Tech Lead)", "project_lead", "usr-lead-01"),
            ("contributor@devmatrix.local", "Elena Rostova (Senior Engineer)", "contributor", "usr-contrib-01"),
        ]

        for email, full_name, role, usr_id in roles_data:
            existing_user = db.query(User).filter(User.email == email).first()
            if not existing_user:
                u = User(
                    id=usr_id,
                    tenant_id=tenant.id,
                    email=email,
                    full_name=full_name,
                    hashed_password=demo_password_hash,
                    role=role,
                    is_active=True,
                )
                db.add(u)
                print(f"  [+] Created user: {email} ({role})")

        # 3. Default Project
        project = db.query(Project).filter(Project.id == "proj-default").first()
        if not project:
            project = Project(
                id="proj-default",
                tenant_id=tenant.id,
                name="Cloud Migration & Core Platform Modernization",
                description="Enterprise initiative to migrate legacy on-prem services to Kubernetes microservices with zero downtime, audit compliance, and automated CI/CD.",
                status="planning",
                target_budget=250000.0,
                currency="USD",
                target_deadline="2026-12-15",
                active_baseline_version="1",
                created_by_id="usr-manager-01",
            )
            db.add(project)
            db.flush()
            print("  [+] Created sample project: Cloud Migration & Core Platform Modernization")

        # Link any unlinked documents to this project
        unlinked_docs = db.query(Document).filter((Document.project_id == None) | (Document.project_id == "")).all()
        for doc in unlinked_docs:
            doc.project_id = project.id
            doc.tenant_id = tenant.id
        if unlinked_docs:
            print(f"  [+] Linked {len(unlinked_docs)} existing documents to default project.")

        # 4. Workforce Profiles
        workforce_data = [
            ("wf-01", "Elena Rostova", "Senior Full-Stack Engineer", 115.0, ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL"], 6.5, 90.0, 40.0, 1),
            ("wf-02", "Marcus Brody", "Cloud DevOps Architect", 145.0, ["Kubernetes", "AWS", "Terraform", "Docker", "CI/CD", "Helm"], 8.0, 80.0, 40.0, 2),
            ("wf-03", "Priya Sharma", "QA Automation Specialist", 90.0, ["Playwright", "Pytest", "Jest", "Performance Testing", "API Testing"], 5.0, 100.0, 40.0, 1),
            ("wf-04", "Kenji Sato", "Data & AI Systems Engineer", 150.0, ["PyTorch", "FastAPI", "Vector DBs", "LangChain", "Data Pipelines"], 7.0, 75.0, 40.0, 2),
            ("wf-05", "David Chen", "Project Lead & Solutions Architect", 130.0, ["Architecture", "System Design", "Agile", "Risk Management", "Security"], 9.0, 85.0, 40.0, 1),
            ("wf-06", "Chloe Bennett", "Frontend UI/UX Specialist", 95.0, ["React", "TypeScript", "Tailwind CSS", "Accessibility", "Design Systems"], 4.5, 95.0, 40.0, 1),
        ]

        for wf_id, name, role, rate, skills, exp, avail, max_hrs, proj_cnt in workforce_data:
            existing_wf = db.query(WorkforceMember).filter(WorkforceMember.id == wf_id).first()
            if not existing_wf:
                wf = WorkforceMember(
                    id=wf_id,
                    tenant_id=tenant.id,
                    full_name=name,
                    role=role,
                    hourly_rate=rate,
                    currency="USD",
                    skills_json=json.dumps(skills),
                    experience_years=exp,
                    availability_pct=avail,
                    max_weekly_hours=max_hrs,
                    active_projects_count=proj_cnt,
                )
                db.add(wf)
                print(f"  [+] Added workforce profile: {name} ({role})")

        # 5. Audit Log Entry
        db.add(
            AuditLog(
                tenant_id=tenant.id,
                user_email="system@devmatrix.local",
                action="demo_seed_completed",
                entity_type="system",
                entity_id=tenant.id,
                details_json=json.dumps({"message": "Demonstration seed completed successfully"}),
            )
        )

        db.commit()
        print("[SUCCESS] Demo seeding complete! You can sign in with:")
        print("   Delivery Manager: manager@devmatrix.local / DevMatrix2026!")
        print("   Tenant Admin:     admin@devmatrix.local / DevMatrix2026!")
        print("   Project Lead:     lead@devmatrix.local / DevMatrix2026!")
        print("   Contributor:      contributor@devmatrix.local / DevMatrix2026!")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Demo seeding failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
