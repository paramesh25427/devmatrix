import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, AuthenticatedUser
from app.models.document import Document
from app.models.project import Project
from app.models.requirement import RequirementDraft
from app.models.baseline import RequirementBaseline
from app.schemas.document import ExtractionResult
from app.schemas.requirement import (
    ProjectRequirementsData,
    ProviderAttemptLog,
    RequirementDraftResponse,
    ReviewUpdateRequest,
)
from app.services.ai.exceptions import AllProvidersFailedError
from app.services.ai.router import AIFallbackRouter

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


@router.post("/extract/{document_id}", response_model=RequirementDraftResponse, status_code=status.HTTP_201_CREATED)
async def extract_project_requirements(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequirementDraftResponse:
    """
    Triggers AI requirement extraction for an uploaded project document.
    Executes sequential fallback: Google Gemini -> xAI Grok -> NVIDIA NIM.
    Returns a validated requirement draft awaiting manager review.
    """
    # 1. Verify document exists in database and belongs to authenticated tenant
    doc = db.query(Document).filter(Document.id == document_id, Document.tenant_id == current_user.tenant_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    # 2. Verify document has extractable text content
    if not doc.has_text or (doc.total_words or 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no extractable text content to process with AI.",
        )

    # 3. Load extraction artifact from storage
    extracted_json_path = os.path.join(settings.extracted_dir, f"{document_id}.json")
    if not os.path.exists(extracted_json_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The extracted content artifact for document '{document_id}' is missing. Please re-upload or re-process the document.",
        )

    try:
        with open(extracted_json_path, "r", encoding="utf-8") as f:
            extraction_dict = json.load(f)
            extraction = ExtractionResult.model_validate(extraction_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read document extraction cache.",
        ) from exc

    # 4. Invoke Central AI Fallback Router
    router_instance = AIFallbackRouter()
    try:
        req_data, provider_used, model_used, attempt_history = await router_instance.extract_requirements(extraction)
    except AllProvidersFailedError as all_fail_err:
        # Document remains intact and preserved in SQLite; return clear, retryable error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "All configured AI providers in fallback sequence failed to produce validated requirements.",
                "attempts": all_fail_err.attempt_history,
                "document_preserved": True,
            },
        ) from all_fail_err

    # 5. Persist draft requirements JSON payload
    draft_id = str(uuid.uuid4())
    raw_json_path = os.path.join(settings.requirements_dir, f"{draft_id}.json")
    try:
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(req_data.model_dump(), f, ensure_ascii=False, indent=2)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist requirements draft payload.",
        ) from exc

    # 6. Persist draft record in SQLite
    attempts_dicts = [a.model_dump() for a in attempt_history]
    draft_record = RequirementDraft(
        id=draft_id,
        tenant_id=current_user.tenant_id,
        project_id=doc.project_id or "proj-default",
        document_id=doc.id,
        document_name=doc.original_filename,
        provider_used=provider_used,
        model_used=model_used,
        status="draft_ready",
        review_status="pending_review",
        summary=req_data.project_summary[:500] if req_data.project_summary else None,
        overall_confidence=req_data.overall_confidence,
        raw_json_path=raw_json_path,
        attempt_history_json=json.dumps(attempts_dicts),
    )

    db.add(draft_record)
    db.commit()
    db.refresh(draft_record)

    return RequirementDraftResponse(
        id=draft_record.id,
        document_id=draft_record.document_id,
        document_name=draft_record.document_name,
        provider_used=draft_record.provider_used,
        model_used=draft_record.model_used,
        status=draft_record.status,
        review_status=draft_record.review_status,
        manager_notes=draft_record.manager_notes,
        attempt_history=attempt_history,
        requirements=req_data,
        created_at=draft_record.created_at,
        updated_at=draft_record.updated_at,
    )


@router.get("/{draft_id}", response_model=RequirementDraftResponse)
def get_requirement_draft(
    draft_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequirementDraftResponse:
    """Retrieves a specific requirements draft along with full validated requirements."""
    draft = (
        db.query(RequirementDraft)
        .filter(RequirementDraft.id == draft_id, RequirementDraft.tenant_id == current_user.tenant_id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement draft '{draft_id}' not found.",
        )

    # Load requirements JSON payload
    req_data = None
    if draft.raw_json_path and os.path.exists(draft.raw_json_path):
        try:
            with open(draft.raw_json_path, "r", encoding="utf-8") as f:
                raw_dict = json.load(f)
                req_data = ProjectRequirementsData.model_validate(raw_dict)
        except Exception:
            req_data = None

    attempts = []
    if draft.attempt_history_json:
        try:
            attempts_raw = json.load(draft.attempt_history_json) if isinstance(draft.attempt_history_json, str) else []
            attempts = [ProviderAttemptLog.model_validate(a) for a in json.loads(draft.attempt_history_json)]
        except Exception:
            attempts = []

    return RequirementDraftResponse(
        id=draft.id,
        document_id=draft.document_id,
        document_name=draft.document_name,
        provider_used=draft.provider_used,
        model_used=draft.model_used,
        status=draft.status,
        review_status=draft.review_status,
        manager_notes=draft.manager_notes,
        attempt_history=attempts,
        requirements=req_data,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


@router.get("/document/{document_id}", response_model=List[RequirementDraftResponse])
def get_document_requirement_drafts(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RequirementDraftResponse]:
    """Retrieves all requirement drafts created for a specific document."""
    doc = db.query(Document).filter(Document.id == document_id, Document.tenant_id == current_user.tenant_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    drafts = (
        db.query(RequirementDraft)
        .filter(RequirementDraft.document_id == document_id, RequirementDraft.tenant_id == current_user.tenant_id)
        .order_by(RequirementDraft.created_at.desc())
        .all()
    )
    results = []
    for draft in drafts:
        req_data = None
        if draft.raw_json_path and os.path.exists(draft.raw_json_path):
            try:
                with open(draft.raw_json_path, "r", encoding="utf-8") as f:
                    raw_dict = json.load(f)
                    req_data = ProjectRequirementsData.model_validate(raw_dict)
            except Exception:
                req_data = None

        attempts = []
        if draft.attempt_history_json:
            try:
                attempts = [ProviderAttemptLog.model_validate(a) for a in json.loads(draft.attempt_history_json)]
            except Exception:
                attempts = []

        results.append(
            RequirementDraftResponse(
                id=draft.id,
                document_id=draft.document_id,
                document_name=draft.document_name,
                provider_used=draft.provider_used,
                model_used=draft.model_used,
                status=draft.status,
                review_status=draft.review_status,
                manager_notes=draft.manager_notes,
                attempt_history=attempts,
                requirements=req_data,
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
        )
    return results


@router.patch("/{draft_id}/review", response_model=RequirementDraftResponse)
def update_manager_review(
    draft_id: str,
    payload: ReviewUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_roles(["tenant_admin", "delivery_manager"])),
    db: Session = Depends(get_db),
) -> RequirementDraftResponse:
    """
    Records a human manager review decision (approved, rejected, pending_review)
    and optional feedback notes.
    """
    draft = (
        db.query(RequirementDraft)
        .filter(RequirementDraft.id == draft_id, RequirementDraft.tenant_id == current_user.tenant_id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement draft '{draft_id}' not found.",
        )

    valid_statuses = ("approved", "rejected", "pending_review")
    if payload.review_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid review status '{payload.review_status}'. Allowed values: {', '.join(valid_statuses)}.",
        )

    draft.review_status = payload.review_status
    if payload.manager_notes is not None:
        draft.manager_notes = payload.manager_notes

    db.commit()
    db.refresh(draft)

    # Load requirements JSON payload
    req_data = None
    if draft.raw_json_path and os.path.exists(draft.raw_json_path):
        try:
            with open(draft.raw_json_path, "r", encoding="utf-8") as f:
                raw_dict = json.load(f)
                req_data = ProjectRequirementsData.model_validate(raw_dict)
        except Exception:
            req_data = None

    attempts = []
    if draft.attempt_history_json:
        try:
            attempts = [ProviderAttemptLog.model_validate(a) for a in json.loads(draft.attempt_history_json)]
        except Exception:
            attempts = []

    return RequirementDraftResponse(
        id=draft.id,
        document_id=draft.document_id,
        document_name=draft.document_name,
        provider_used=draft.provider_used,
        model_used=draft.model_used,
        status=draft.status,
        review_status=draft.review_status,
        manager_notes=draft.manager_notes,
        attempt_history=attempts,
        requirements=req_data,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


class BaselineApprovalRequest(BaseModel):
    manager_notes: Optional[str] = None
    change_summary: Optional[str] = "Approved initial requirements baseline"


class BaselineResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    version: int
    draft_id: str
    approved_by_id: str
    approved_by_name: str
    approved_at: datetime
    requirements: Dict[str, Any]
    change_summary: Optional[str]
    is_active: bool


@router.post("/draft/{draft_id}/approve", response_model=BaselineResponse)
def approve_requirements_baseline(
    draft_id: str,
    payload: BaselineApprovalRequest,
    current_user: AuthenticatedUser = Depends(require_roles(["tenant_admin", "delivery_manager"])),
    db: Session = Depends(get_db),
):
    """
    Managerial action: Approves a draft into an immutable, versioned RequirementBaseline.
    Downstream planning (WBS, estimation, risks, workforce) requires an approved baseline.
    """
    draft = (
        db.query(RequirementDraft)
        .filter(RequirementDraft.id == draft_id, RequirementDraft.tenant_id == current_user.tenant_id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement draft '{draft_id}' not found.",
        )

    # Read requirements JSON payload
    req_json_str = "{}"
    if draft.raw_json_path and os.path.exists(draft.raw_json_path):
        with open(draft.raw_json_path, "r", encoding="utf-8") as f:
            req_json_str = f.read()

    project_id = draft.project_id or "proj-default"
    tenant_id = current_user.tenant_id

    # Compute next version number
    latest_baseline = (
        db.query(RequirementBaseline)
        .filter(RequirementBaseline.tenant_id == tenant_id, RequirementBaseline.project_id == project_id)
        .order_by(RequirementBaseline.version.desc())
        .first()
    )
    next_version = (latest_baseline.version + 1) if latest_baseline else 1

    # Mark prior baselines inactive
    db.query(RequirementBaseline).filter(
        RequirementBaseline.tenant_id == tenant_id,
        RequirementBaseline.project_id == project_id,
    ).update({"is_active": False})

    # Create new baseline
    baseline_id = str(uuid.uuid4())
    baseline = RequirementBaseline(
        id=baseline_id,
        tenant_id=tenant_id,
        project_id=project_id,
        version=next_version,
        draft_id=draft.id,
        approved_by_id=current_user.id,
        approved_by_name=current_user.email,
        approved_at=datetime.utcnow(),
        requirements_data_json=req_json_str,
        change_summary=payload.change_summary,
        is_active=True,
    )
    db.add(baseline)

    # Update draft
    draft.review_status = "approved"
    draft.is_approved_baseline = True
    draft.version = next_version
    draft.approved_by_id = current_user.id
    draft.approved_at = datetime.utcnow()
    if payload.manager_notes:
        draft.manager_notes = payload.manager_notes

    # Update project active baseline
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.active_baseline_version = str(next_version)
        if project.status == "intake":
            project.status = "planning"

    # Log audit record
    from app.models.audit import AuditLog
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="baseline_approved",
            entity_type="requirement_baseline",
            entity_id=baseline_id,
            details_json=json.dumps({"version": next_version, "draft_id": draft_id}),
        )
    )

    db.commit()
    db.refresh(baseline)

    return BaselineResponse(
        id=baseline.id,
        tenant_id=baseline.tenant_id,
        project_id=baseline.project_id,
        version=baseline.version,
        draft_id=baseline.draft_id,
        approved_by_id=baseline.approved_by_id,
        approved_by_name=baseline.approved_by_name,
        approved_at=baseline.approved_at,
        requirements=json.loads(baseline.requirements_data_json),
        change_summary=baseline.change_summary,
        is_active=baseline.is_active,
    )


@router.get("/baseline/{project_id}", response_model=BaselineResponse)
def get_active_baseline(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves the current active approved baseline for a project."""
    baseline = (
        db.query(RequirementBaseline)
        .filter(
            RequirementBaseline.tenant_id == current_user.tenant_id,
            RequirementBaseline.project_id == project_id,
            RequirementBaseline.is_active == True,
        )
        .order_by(RequirementBaseline.version.desc())
        .first()
    )
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No approved requirements baseline found for project '{project_id}'. A delivery manager must approve a requirements draft first.",
        )

    return BaselineResponse(
        id=baseline.id,
        tenant_id=baseline.tenant_id,
        project_id=baseline.project_id,
        version=baseline.version,
        draft_id=baseline.draft_id,
        approved_by_id=baseline.approved_by_id,
        approved_by_name=baseline.approved_by_name,
        approved_at=baseline.approved_at,
        requirements=json.loads(baseline.requirements_data_json),
        change_summary=baseline.change_summary,
        is_active=baseline.is_active,
    )


@router.get("/baselines/{project_id}", response_model=List[BaselineResponse])
def list_project_baselines(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves full version history of all baselines for a project."""
    baselines = (
        db.query(RequirementBaseline)
        .filter(
            RequirementBaseline.tenant_id == current_user.tenant_id,
            RequirementBaseline.project_id == project_id,
        )
        .order_by(RequirementBaseline.version.desc())
        .all()
    )
    return [
        BaselineResponse(
            id=b.id,
            tenant_id=b.tenant_id,
            project_id=b.project_id,
            version=b.version,
            draft_id=b.draft_id,
            approved_by_id=b.approved_by_id,
            approved_by_name=b.approved_by_name,
            approved_at=b.approved_at,
            requirements=json.loads(b.requirements_data_json),
            change_summary=b.change_summary,
            is_active=b.is_active,
        )
        for b in baselines
    ]
