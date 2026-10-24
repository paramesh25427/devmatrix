import json
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, AuthenticatedUser
from app.models.document import Document
from app.models.project import Project
from app.models.audit import AuditLog
from app.models.requirement import RequirementDraft
from app.schemas.document import DocumentDetail, DocumentSummary, ExtractionResult
from app.services.extractor import DocumentExtractor, sanitize_filename, validate_file_magic_bytes

router = APIRouter(prefix="/api/documents", tags=["documents"])


UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB bounded chunk size


@router.post("/upload", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    """
    Intake and process a single project document.
    Enforces authentication and scopes the document to the user's tenant.
    Validates file extension, magic signature, and size limit in bounded chunks.
    Performs structured text/table extraction and persists metadata and extracted content.
    Cleans up temporary artifacts on failure or size violation.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )

    # 1. Sanitize original filename and extract extension
    safe_name = sanitize_filename(file.filename)
    parts = safe_name.rsplit(".", 1)
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File has no extension. Please provide a supported file type.",
        )

    ext = parts[1].lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: {', '.join(settings.allowed_extensions)}.",
        )

    created_files: List[str] = []
    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}.{ext}"
    saved_file_path = os.path.join(settings.uploads_dir, stored_filename)

    try:
        # 2. Read first bounded chunk to validate presence and magic signature
        first_chunk = await file.read(UPLOAD_CHUNK_SIZE)
        if not first_chunk or len(first_chunk) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty (0 bytes).",
            )

        # 3. Validate magic bytes / content integrity on initial chunk
        is_valid, validation_err = validate_file_magic_bytes(first_chunk, ext)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_err,
            )

        total_bytes = len(first_chunk)
        if total_bytes > settings.max_upload_size_bytes:
            max_mb = settings.max_upload_size_bytes / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_mb:.1f} MB.",
            )

        # 4. Stream upload in bounded chunks directly to server storage
        try:
            with open(saved_file_path, "wb") as out_f:
                out_f.write(first_chunk)
                created_files.append(saved_file_path)

                while True:
                    chunk = await file.read(UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > settings.max_upload_size_bytes:
                        max_mb = settings.max_upload_size_bytes / (1024 * 1024)
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=f"File exceeds maximum allowed size of {max_mb:.1f} MB.",
                        )
                    out_f.write(chunk)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store document on server.",
            ) from exc

        # 5. Extract structured content
        extraction = DocumentExtractor.extract(
            file_path=saved_file_path,
            original_filename=safe_name,
            file_type=ext,
            document_id=doc_id,
        )

        # 6. Save extracted content as JSON artifact on file system
        extracted_json_path = os.path.join(settings.extracted_dir, f"{doc_id}.json")
        try:
            with open(extracted_json_path, "w", encoding="utf-8") as f:
                json.dump(extraction.model_dump(), f, ensure_ascii=False, indent=2)
            created_files.append(extracted_json_path)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist extraction JSON cache.",
            ) from exc

        # 7. Persist metadata record in SQLite
        tenant_id = current_user.tenant_id
        proj_id = project_id or "proj-default"
        if proj_id != "proj-default":
            proj = db.query(Project).filter(Project.id == proj_id, Project.tenant_id == tenant_id).first()
            if not proj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project '{proj_id}' not found in your organization.",
                )

        doc_record = Document(
            id=doc_id,
            tenant_id=tenant_id,
            project_id=proj_id,
            original_filename=safe_name,
            stored_filename=stored_filename,
            file_type=ext,
            file_size_bytes=total_bytes,
            mime_type=file.content_type,
            extraction_status=extraction.status,
            error_message=extraction.warnings[0] if extraction.status == "failed" and extraction.warnings else None,
            warning_message="; ".join(extraction.warnings) if extraction.status == "warning" and extraction.warnings else None,
            total_pages=extraction.total_pages,
            total_sheets=extraction.total_sheets,
            total_words=extraction.total_words,
            has_text=extraction.has_text,
        )

        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        # Successful transaction: clear tracking list so files are preserved
        created_files.clear()

        return DocumentDetail(
            id=doc_record.id,
            tenant_id=doc_record.tenant_id,
            project_id=doc_record.project_id,
            original_filename=doc_record.original_filename,
            file_type=doc_record.file_type,
            file_size_bytes=doc_record.file_size_bytes,
            extraction_status=doc_record.extraction_status,
            error_message=doc_record.error_message,
            warning_message=doc_record.warning_message,
            total_pages=doc_record.total_pages,
            total_sheets=doc_record.total_sheets,
            total_words=doc_record.total_words,
            has_text=doc_record.has_text,
            created_at=doc_record.created_at,
            extraction=extraction,
        )

    except HTTPException:
        # Roll back and remove any files created for this upload attempt
        db.rollback()
        for fpath in created_files:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass
        raise
    except Exception as exc:
        # Unexpected error: roll back transaction and remove newly created files
        db.rollback()
        for fpath in created_files:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected failure during document intake and persistence.",
        ) from exc
    finally:
        await file.close()


@router.get("", response_model=List[DocumentSummary])
def list_documents(
    project_id: Optional[str] = Query(None, description="Optional project ID to filter documents"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DocumentSummary]:
    """Retrieve list of documents uploaded by the authenticated user's tenant with summary statistics."""
    query = db.query(Document).filter(Document.tenant_id == current_user.tenant_id)
    if project_id:
        query = query.filter(Document.project_id == project_id)
    docs = query.order_by(Document.created_at.desc()).all()
    return [DocumentSummary.model_validate(doc) for doc in docs]


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(
    doc_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    """Retrieve a specific document's metadata along with full extracted content, scoped to tenant."""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.tenant_id == current_user.tenant_id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found.",
        )

    # Load extraction details from stored JSON
    extracted_json_path = os.path.join(settings.extracted_dir, f"{doc_id}.json")
    extraction = None
    if os.path.exists(extracted_json_path):
        try:
            with open(extracted_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                extraction = ExtractionResult.model_validate(data)
        except Exception:
            extraction = None

    return DocumentDetail(
        id=doc.id,
        tenant_id=doc.tenant_id,
        project_id=doc.project_id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        extraction_status=doc.extraction_status,
        error_message=doc.error_message,
        warning_message=doc.warning_message,
        total_pages=doc.total_pages,
        total_sheets=doc.total_sheets,
        total_words=doc.total_words,
        has_text=doc.has_text,
        created_at=doc.created_at,
        extraction=extraction,
    )


@router.get("/{doc_id}/download")
def download_document(
    doc_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Securely stream/download an uploaded document file, enforcing tenant ownership."""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.tenant_id == current_user.tenant_id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found.",
        )

    raw_path = os.path.join(settings.uploads_dir, doc.stored_filename)
    if not os.path.exists(raw_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document binary file is missing from server storage.",
        )

    return FileResponse(
        path=raw_path,
        filename=doc.original_filename,
        media_type=doc.mime_type or "application/octet-stream",
    )


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(
    doc_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(["tenant_admin", "delivery_manager"])),
    db: Session = Depends(get_db),
):
    """Delete a document record and clean up associated stored files, restricted to managers/admins."""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.tenant_id == current_user.tenant_id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found.",
        )

    # Remove storage files if present
    raw_path = os.path.join(settings.uploads_dir, doc.stored_filename)
    if os.path.exists(raw_path):
        try:
            os.remove(raw_path)
        except OSError:
            pass

    extracted_path = os.path.join(settings.extracted_dir, f"{doc_id}.json")
    if os.path.exists(extracted_path):
        try:
            os.remove(extracted_path)
        except OSError:
            pass

    # Audit logging for security compliance
    db.add(
        AuditLog(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="document_deleted",
            entity_type="document",
            entity_id=doc_id,
            details_json=json.dumps({"original_filename": doc.original_filename, "file_size_bytes": doc.file_size_bytes}),
        )
    )

    # Check for linked requirement drafts
    linked_drafts = (
        db.query(RequirementDraft)
        .filter(RequirementDraft.document_id == doc_id, RequirementDraft.tenant_id == current_user.tenant_id)
        .all()
    )

    # 1. Block deletion if any linked draft is an approved baseline
    for draft in linked_drafts:
        if draft.is_approved_baseline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete document '{doc.original_filename}' because it is linked to an approved requirements baseline. Archive the baseline first.",
            )

    # 2. Clean up linked unapproved drafts to prevent orphaned records
    for draft in linked_drafts:
        if draft.raw_json_path and os.path.exists(draft.raw_json_path):
            try:
                os.remove(draft.raw_json_path)
            except OSError:
                pass
        db.delete(draft)

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully", "id": doc_id}
