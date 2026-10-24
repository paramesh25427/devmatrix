import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_projects_unauthenticated():
    """Verify that accessing projects without authorization returns 401 Unauthorized."""
    response = client.get("/api/projects")
    assert response.status_code == 401
    assert "Not authenticated" in response.text or "detail" in response.json()


def test_get_projects_authenticated(auth_headers_tenant_a):
    """Verify authenticated user receives their tenant's projects."""
    response = client.get("/api/projects", headers=auth_headers_tenant_a)
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    assert len(projects) >= 1
    # Check project structure
    project_ids = [p["id"] for p in projects]
    assert "proj-default" in project_ids
    for p in projects:
        assert "id" in p
        assert "name" in p
        assert "tenant_id" in p
        assert p["tenant_id"] == "tenant-default"


def test_tenant_isolation_projects(auth_headers_tenant_a, auth_headers_tenant_b):
    """Verify Tenant A cannot see Tenant B's projects and vice versa."""
    res_a = client.get("/api/projects", headers=auth_headers_tenant_a)
    assert res_a.status_code == 200
    projects_a = res_a.json()
    ids_a = [p["id"] for p in projects_a]
    assert "proj-default" in ids_a
    assert "proj-beta" not in ids_a

    res_b = client.get("/api/projects", headers=auth_headers_tenant_b)
    assert res_b.status_code == 200
    projects_b = res_b.json()
    ids_b = [p["id"] for p in projects_b]
    assert "proj-beta" in ids_b
    assert "proj-default" not in ids_b


def test_create_project_authenticated(auth_headers_tenant_a):
    """Verify authenticated delivery manager can create a new project in their tenant."""
    payload = {
        "name": "Cloud Transformation 2026",
        "description": "Enterprise cloud modernization intake",
        "status": "intake",
    }
    response = client.post("/api/projects", json=payload, headers=auth_headers_tenant_a)
    assert response.status_code in [200, 201]
    created = response.json()
    assert created["name"] == "Cloud Transformation 2026"
    assert created["tenant_id"] == "tenant-default"
    assert "id" in created

    # Verify it now appears in project list
    list_res = client.get("/api/projects", headers=auth_headers_tenant_a)
    assert list_res.status_code == 200
    ids = [p["id"] for p in list_res.json()]
    assert created["id"] in ids


def test_get_project_by_id_tenant_isolation(auth_headers_tenant_a, auth_headers_tenant_b):
    """Verify tenant isolation on GET /api/projects/{id}."""
    # Tenant A accesses their project -> 200
    res_ok = client.get("/api/projects/proj-default", headers=auth_headers_tenant_a)
    assert res_ok.status_code == 200
    assert res_ok.json()["id"] == "proj-default"

    # Tenant A attempts to access Tenant B's project -> 404
    res_forbidden = client.get("/api/projects/proj-beta", headers=auth_headers_tenant_a)
    assert res_forbidden.status_code == 404
