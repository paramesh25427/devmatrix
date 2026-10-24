import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.job import BackgroundJob
from app.models.document import Document
from app.services.jobs.manager import JobManager
from app.services.requirements.worker import execute_async_extraction_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobStatusResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: Optional[str]
    document_id: Optional[str]
    job_type: str
    status: str
    progress_pct: int
    message: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[Dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


@router.post("/extract/{document_id}", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_extraction_job(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiates an asynchronous, observable AI requirement extraction job.
    Returns HTTP 202 with job_id immediately without blocking the browser.
    Prevents duplicate concurrent jobs for the same document.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.tenant_id == current_user.tenant_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    if not doc.has_text or (doc.total_words or 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no extractable text content to process with AI.",
        )

    # Create queued job in DB
    job = JobManager.create_job(
        db=db,
        tenant_id=current_user.tenant_id,
        job_type="requirement_extraction",
        project_id=doc.project_id or "proj-default",
        document_id=doc.id,
        message="Queued for AI requirement extraction",
    )

    # Launch background task if newly queued
    if job.status == "queued":
        JobManager.launch_job(
            job.id,
            execute_async_extraction_job,
            document_id=doc.id,
            tenant_id=current_user.tenant_id,
            project_id=doc.project_id,
        )

    return JobStatusResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        project_id=job.project_id,
        document_id=job.document_id,
        job_type=job.job_type,
        status=job.status,
        progress_pct=job.progress_pct,
        message=job.message,
        result=json.loads(job.result_json) if job.result_json else None,
        error=json.loads(job.error_json) if job.error_json else None,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Polls the execution status and progress percentage of an observable background job."""
    job = (
        db.query(BackgroundJob)
        .filter(BackgroundJob.id == job_id, BackgroundJob.tenant_id == current_user.tenant_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID '{job_id}' not found.")

    return JobStatusResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        project_id=job.project_id,
        document_id=job.document_id,
        job_type=job.job_type,
        status=job.status,
        progress_pct=job.progress_pct,
        message=job.message,
        result=json.loads(job.result_json) if job.result_json else None,
        error=json.loads(job.error_json) if job.error_json else None,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancels an active or queued background job."""
    job = (
        db.query(BackgroundJob)
        .filter(BackgroundJob.id == job_id, BackgroundJob.tenant_id == current_user.tenant_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID '{job_id}' not found.")

    cancelled = JobManager.cancel_job(job_id)
    return {"job_id": job_id, "cancelled": cancelled}
