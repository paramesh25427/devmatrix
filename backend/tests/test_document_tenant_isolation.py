import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_unauthenticated_requests_fail_401():
    """Verify that unauthenticated requests to all document and extraction endpoints strictly return 401."""
    # Upload
    res = client.post("/api/documents/upload", files={"file": ("test.txt", b"content", "text/plain")})
    assert res.status_code == 401

    # List
    res = client.get("/api/documents")
    assert res.status_code == 401

    # Get
    res = client.get("/api/documents/non-existent-id")
    assert res.status_code == 401

    # Download
    res = client.get("/api/documents/non-existent-id/download")
    assert res.status_code == 401

    # Delete
    res = client.delete("/api/documents/non-existent-id")
    assert res.status_code == 401

    # Requirements extract
    res = client.post("/api/requirements/extract/non-existent-id")
    assert res.status_code == 401

    # Jobs extract
    res = client.post("/api/jobs/extract/non-existent-id")
    assert res.status_code == 401


def test_tenant_isolation_upload_list_and_get(auth_headers_tenant_a, auth_headers_tenant_b):
    """
    Verify Tenant A uploads a document and Tenant B cannot see or get it.
    Changing IDs gives 404 to prevent document enumeration.
    """
    # 1. Tenant A uploads a document
    doc_content = b"Confidential Strategy Document for Tenant A\nKey priorities and roadmaps."
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("strategy_a.txt", doc_content, "text/plain")},
        headers=auth_headers_tenant_a,
    )
    assert upload_res.status_code == 201
    doc_a = upload_res.json()
    doc_a_id = doc_a["id"]
    assert doc_a["tenant_id"] == "tenant-default"
    assert doc_a["original_filename"] == "strategy_a.txt"

    # 2. Tenant A can list and retrieve their own document
    list_a = client.get("/api/documents", headers=auth_headers_tenant_a)
    assert list_a.status_code == 200
    ids_a = [d["id"] for d in list_a.json()]
    assert doc_a_id in ids_a

    get_a = client.get(f"/api/documents/{doc_a_id}", headers=auth_headers_tenant_a)
    assert get_a.status_code == 200
    assert get_a.json()["id"] == doc_a_id

    # 3. Tenant B lists documents: Tenant A's document must NOT appear
    list_b = client.get("/api/documents", headers=auth_headers_tenant_b)
    assert list_b.status_code == 200
    ids_b = [d["id"] for d in list_b.json()]
    assert doc_a_id not in ids_b

    # 4. Tenant B attempts to GET Tenant A's document by ID: must return 404 (anti-enumeration)
    get_b = client.get(f"/api/documents/{doc_a_id}", headers=auth_headers_tenant_b)
    assert get_b.status_code == 404
    assert f"Document with ID '{doc_a_id}' not found." in get_b.json()["detail"]


def test_tenant_isolation_download(auth_headers_tenant_a, auth_headers_tenant_b):
    """Verify Tenant B cannot download Tenant A's document file."""
    # Tenant A uploads
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("deliverables_a.txt", b"Tenant A Deliverables Content", "text/plain")},
        headers=auth_headers_tenant_a,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Tenant A downloads: 200 OK
    dl_a = client.get(f"/api/documents/{doc_id}/download", headers=auth_headers_tenant_a)
    assert dl_a.status_code == 200
    assert dl_a.content == b"Tenant A Deliverables Content"

    # Tenant B attempts download: 404 NOT FOUND
    dl_b = client.get(f"/api/documents/{doc_id}/download", headers=auth_headers_tenant_b)
    assert dl_b.status_code == 404


def test_tenant_isolation_extraction_and_jobs(auth_headers_tenant_a, auth_headers_tenant_b):
    """Verify Tenant B cannot trigger requirement extraction or background jobs on Tenant A's document."""
    # Tenant A uploads
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("project_spec_a.txt", b"DevMatrix requirements and technical specs.", "text/plain")},
        headers=auth_headers_tenant_a,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Tenant B tries to trigger AI extraction on Tenant A's document: 404 NOT FOUND
    ext_b = client.post(f"/api/requirements/extract/{doc_id}", headers=auth_headers_tenant_b)
    assert ext_b.status_code == 404

    # Tenant B tries to trigger background job on Tenant A's document: 404 NOT FOUND
    job_b = client.post(f"/api/jobs/extract/{doc_id}", headers=auth_headers_tenant_b)
    assert job_b.status_code == 404


def test_role_restricted_deletion_and_cross_tenant_delete(
    auth_headers_tenant_a,
    auth_headers_tenant_b,
    auth_headers_contributor_a,
):
    """
    Verify deletion permissions:
    1. Tenant B cannot delete Tenant A's document (returns 404).
    2. Contributor in Tenant A cannot delete Tenant A's document (returns 403).
    3. Delivery manager in Tenant A can delete Tenant A's document (returns 200).
    """
    # Tenant A uploads
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("temp_delete_doc.txt", b"Temporary file for deletion test", "text/plain")},
        headers=auth_headers_tenant_a,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 1. Tenant B tries to delete Tenant A's document: 404
    del_b = client.delete(f"/api/documents/{doc_id}", headers=auth_headers_tenant_b)
    assert del_b.status_code == 404

    # 2. Contributor in Tenant A tries to delete: 403 Forbidden
    del_contrib = client.delete(f"/api/documents/{doc_id}", headers=auth_headers_contributor_a)
    assert del_contrib.status_code == 403
    assert "Access denied" in del_contrib.json()["detail"]

    # 3. Delivery Manager in Tenant A deletes: 200 OK
    del_mgr = client.delete(f"/api/documents/{doc_id}", headers=auth_headers_tenant_a)
    assert del_mgr.status_code == 200
    assert del_mgr.json()["id"] == doc_id

    # Verify document is gone
    get_after = client.get(f"/api/documents/{doc_id}", headers=auth_headers_tenant_a)
    assert get_after.status_code == 404


def test_cross_tenant_project_assignment_prevention(auth_headers_tenant_a):
    """Verify that a user from Tenant A cannot attach an uploaded document to Tenant B's project."""
    res = client.post(
        "/api/documents/upload",
        files={"file": ("illegal_project.txt", b"Document content", "text/plain")},
        data={"project_id": "proj-beta"},  # proj-beta belongs to Tenant B
        headers=auth_headers_tenant_a,
    )
    assert res.status_code == 404
    assert "not found in your organization" in res.json()["detail"]
