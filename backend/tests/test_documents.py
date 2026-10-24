import io
import os
from unittest.mock import patch
import openpyxl
import pypdf
from docx import Document as DocxDocument
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def set_auth_header():
    """Authenticates client as delivery manager to preserve authorized test workflows."""
    from app.core.security import create_access_token
    token = create_access_token(
        user_id="user-mgr-a",
        email="manager@devmatrix.local",
        role="delivery_manager",
        tenant_id="tenant-default",
    )
    client.headers["Authorization"] = f"Bearer {token}"


@pytest.fixture(autouse=True)
def cleanup_test_storage():
    """Ensure tests run against and leave a clean storage directory."""
    yield
    for folder in (settings.uploads_dir, settings.extracted_dir):
        if os.path.exists(folder):
            for fname in os.listdir(folder):
                fpath = os.path.join(folder, fname)
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                except OSError:
                    pass


def create_synthetic_pdf() -> bytes:
    """Creates a small valid 2-page PDF in-memory."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_synthetic_docx() -> bytes:
    """Creates a small valid DOCX in-memory with text and a table."""
    doc = DocxDocument()
    doc.add_paragraph("DevMatrix AI System Requirements Specification")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Module"
    table.cell(0, 1).text = "Priority"
    table.cell(1, 0).text = "Project Intake"
    table.cell(1, 1).text = "High"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_synthetic_xlsx() -> bytes:
    """Creates a small valid XLSX in-memory with two sheets."""
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Milestones"
    ws1.append(["Phase", "Estimated Weeks"])
    ws1.append(["Intake & Parsing", 2])
    ws1.append(["Planning Engine", 4])

    ws2 = wb.create_sheet(title="Budget")
    ws2.append(["Item", "Cost"])
    ws2.append(["Compute", 500])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_upload_and_extract_txt():
    """Verify TXT upload and extraction."""
    content = b"DevMatrix AI Project Charter\n\nGoals: Automated sprint estimation and skills matching."
    response = client.post(
        "/api/documents/upload",
        files={"file": ("project_charter.txt", content, "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "project_charter.txt"
    assert data["file_type"] == "txt"
    assert data["extraction_status"] == "completed"
    assert data["has_text"] is True
    assert data["total_words"] > 0
    assert len(data["extraction"]["sections"]) >= 1
    assert "Automated sprint estimation" in data["extraction"]["sections"][0]["content"]


def test_upload_and_extract_csv():
    """Verify CSV upload and structured tabular extraction."""
    csv_content = b"Task,Role,Hours\nParser,Backend,16\nViewer,Frontend,12\n"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("tasks.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_type"] == "csv"
    assert data["extraction_status"] == "completed"
    table = data["extraction"]["sections"][0]["table"]
    assert table["headers"] == ["Task", "Role", "Hours"]
    assert len(table["rows"]) == 2
    assert table["rows"][0] == ["Parser", "Backend", "16"]


def test_upload_and_extract_docx():
    """Verify DOCX upload and extraction of paragraphs and tables."""
    docx_bytes = create_synthetic_docx()
    response = client.post(
        "/api/documents/upload",
        files={"file": ("spec.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_type"] == "docx"
    assert data["extraction_status"] == "completed"
    assert data["has_text"] is True


def test_upload_and_extract_xlsx():
    """Verify XLSX upload and extraction across multiple sheets."""
    xlsx_bytes = create_synthetic_xlsx()
    response = client.post(
        "/api/documents/upload",
        files={"file": ("plan.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_type"] == "xlsx"
    assert data["total_sheets"] == 2
    assert data["extraction_status"] == "completed"
    assert len(data["extraction"]["sections"]) == 2


def test_upload_pdf_without_text_reports_warning():
    """Verify PDF with blank pages triggers the 'no extractable text / no OCR' warning."""
    pdf_bytes = create_synthetic_pdf()
    response = client.post(
        "/api/documents/upload",
        files={"file": ("blank_scan.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_type"] == "pdf"
    assert data["total_pages"] == 2
    assert data["has_text"] is False
    assert data["extraction_status"] == "warning"
    assert any("OCR is not supported" in w for w in data["extraction"]["warnings"])


def test_upload_empty_file_rejected():
    """Verify empty (0-byte) file upload is rejected with HTTP 400."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert "File is empty" in response.json()["detail"]


def test_upload_unsupported_format_rejected():
    """Verify unsupported file extension is rejected with HTTP 400."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("payload.exe", b"MZ\x90\x00", "application/x-msdownload")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_corrupt_magic_bytes_rejected():
    """Verify file with .pdf extension but invalid signature is rejected."""
    fake_pdf = b"NOT_A_REAL_PDF_FILE_HEADER"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("corrupt.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    assert "Invalid PDF" in response.json()["detail"]


def test_upload_oversized_file_rejected():
    """Verify file exceeding size limit is rejected with HTTP 413 and leaves no orphaned files."""
    orig_limit = settings.max_upload_size_bytes
    initial_uploads = set(os.listdir(settings.uploads_dir))
    try:
        # Temporarily restrict limit to 100 bytes for test
        settings.max_upload_size_bytes = 100
        oversized = b"A" * 150
        response = client.post(
            "/api/documents/upload",
            files={"file": ("large.txt", oversized, "text/plain")},
        )
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]
        # Verify no file remained in storage/uploads
        current_uploads = set(os.listdir(settings.uploads_dir))
        assert current_uploads == initial_uploads
    finally:
        settings.max_upload_size_bytes = orig_limit


def test_chunked_streaming_size_enforcement_cleans_up_file():
    """Verify multi-chunk file exceeding size limit is rejected during streaming with no file left on disk."""
    orig_limit = settings.max_upload_size_bytes
    initial_uploads = set(os.listdir(settings.uploads_dir))
    try:
        # Set limit to 1.5 MiB
        settings.max_upload_size_bytes = int(1.5 * 1024 * 1024)
        # Create 2.2 MiB payload (crosses 1 MiB chunk boundary)
        chunked_oversized = b"Hello world chunk content!\n" * (100 * 1024)
        response = client.post(
            "/api/documents/upload",
            files={"file": ("stream_large.txt", chunked_oversized, "text/plain")},
        )
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]
        current_uploads = set(os.listdir(settings.uploads_dir))
        assert current_uploads == initial_uploads
    finally:
        settings.max_upload_size_bytes = orig_limit


def test_simulated_persistence_failure_cleanup_and_rollback():
    """Verify unexpected persistence error rolls back DB transaction and removes newly created storage files."""
    # Pre-upload a successful document to ensure previous files are untouched
    pre_res = client.post(
        "/api/documents/upload",
        files={"file": ("existing_doc.txt", b"Existing valid document content.", "text/plain")},
    )
    assert pre_res.status_code == 201
    existing_id = pre_res.json()["id"]

    uploads_after_pre = set(os.listdir(settings.uploads_dir))
    extracted_after_pre = set(os.listdir(settings.extracted_dir))

    # Now attempt an upload where db.commit raises an unhandled database exception
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Simulated SQLite write error")):
        fail_res = client.post(
            "/api/documents/upload",
            files={"file": ("failing_doc.txt", b"Failing document content.", "text/plain")},
        )
        assert fail_res.status_code == 500
        assert "Unexpected failure during document intake and persistence." in fail_res.json()["detail"]

    # Verify that files created for the failing upload were cleaned up
    current_uploads = set(os.listdir(settings.uploads_dir))
    current_extracted = set(os.listdir(settings.extracted_dir))
    assert current_uploads == uploads_after_pre
    assert current_extracted == extracted_after_pre

    # Verify existing document is still present in database
    get_res = client.get(f"/api/documents/{existing_id}")
    assert get_res.status_code == 200

    # Clean up pre-uploaded document
    client.delete(f"/api/documents/{existing_id}")


def test_list_and_get_document():
    """Verify listing documents and retrieving single document details."""
    txt_content = b"Sprint 1 Backlog: Setup authentication and team matrix."
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("sprint.txt", txt_content, "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # List documents
    list_res = client.get("/api/documents")
    assert list_res.status_code == 200
    ids = [d["id"] for d in list_res.json()]
    assert doc_id in ids

    # Get single document
    get_res = client.get(f"/api/documents/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == doc_id
    assert get_res.json()["original_filename"] == "sprint.txt"
    assert get_res.json()["extraction"] is not None


def test_delete_document():
    """Verify document deletion and file cleanup."""
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("temp.txt", b"temporary notes", "text/plain")},
    )
    doc_id = upload_res.json()["id"]

    delete_res = client.delete(f"/api/documents/{doc_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["id"] == doc_id

    # Verify 404 on subsequent get
    get_res = client.get(f"/api/documents/{doc_id}")
    assert get_res.status_code == 404


def test_delete_document_cascades_unapproved_draft():
    """Verify deleting a document cascades its unapproved drafts and cleans up storage files, leaving no orphans."""
    import uuid
    import json
    from tests.conftest import TestingSessionLocal
    from app.models.requirement import RequirementDraft

    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("cascade_test.txt", b"Content for cascade test", "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    draft_id = str(uuid.uuid4())
    draft_file = os.path.join(settings.requirements_dir, f"{draft_id}.json")
    os.makedirs(settings.requirements_dir, exist_ok=True)
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump({"test": "data"}, f)

    db = TestingSessionLocal()
    try:
        draft = RequirementDraft(
            id=draft_id,
            tenant_id="tenant-default",
            project_id="proj-default",
            document_id=doc_id,
            document_name="cascade_test.txt",
            provider_used="gemini",
            model_used="gemini-3.5-flash",
            status="draft_ready",
            review_status="pending_review",
            raw_json_path=draft_file,
            is_approved_baseline=False,
        )
        db.add(draft)
        db.commit()
    finally:
        db.close()

    # Delete document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200

    # Verify document is deleted
    assert client.get(f"/api/documents/{doc_id}").status_code == 404

    # Verify linked draft is deleted (no orphan)
    assert client.get(f"/api/requirements/{draft_id}").status_code == 404

    # Verify storage file was cleaned up
    assert not os.path.exists(draft_file)


def test_delete_document_blocked_when_approved_baseline():
    """Verify deleting a document linked to an approved baseline draft is blocked with 400."""
    import uuid
    from tests.conftest import TestingSessionLocal
    from app.models.requirement import RequirementDraft

    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("baseline_test.txt", b"Content for baseline test", "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    draft_id = str(uuid.uuid4())
    db = TestingSessionLocal()
    try:
        draft = RequirementDraft(
            id=draft_id,
            tenant_id="tenant-default",
            project_id="proj-default",
            document_id=doc_id,
            document_name="baseline_test.txt",
            provider_used="gemini",
            model_used="gemini-3.5-flash",
            status="draft_ready",
            review_status="approved",
            is_approved_baseline=True,
        )
        db.add(draft)
        db.commit()
    finally:
        db.close()

    # Attempt to delete document -> must be blocked
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 400
    assert "approved requirements baseline" in del_res.json()["detail"]

    # Verify document still exists
    assert client.get(f"/api/documents/{doc_id}").status_code == 200

    # Cleanup: unmark baseline and delete
    db = TestingSessionLocal()
    try:
        d = db.query(RequirementDraft).filter(RequirementDraft.id == draft_id).first()
        if d:
            d.is_approved_baseline = False
            db.commit()
    finally:
        db.close()

    cleanup_res = client.delete(f"/api/documents/{doc_id}")
    assert cleanup_res.status_code == 200
