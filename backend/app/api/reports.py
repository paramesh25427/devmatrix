import os
import re
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser, security_scheme, decode_access_token
from app.models.project import Project
from app.models.report import ProjectReport
from app.services.reports.pdf_service import ReportGeneratorService

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportSummaryResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    title: str
    report_type: str
    baseline_version: int
    file_size_bytes: int
    generated_by: str
    created_at: datetime


def get_auth_for_download(
    token: Optional[str] = Query(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> AuthenticatedUser:
    """Supports token from either Authorization header or ?token= query parameter for direct PDF downloads."""
    raw_token = auth.credentials if (auth and auth.credentials) else token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(raw_token)
    user_id = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role")
    tenant_id = payload.get("tenant_id")
    if user_id and role and tenant_id:
        return AuthenticatedUser(id=user_id, email=email or "", role=role, tenant_id=tenant_id)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")


@router.post("/generate/{project_id}", response_model=ReportSummaryResponse, status_code=status.HTTP_201_CREATED)
def generate_project_report(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compiles stored, verified project data (baseline, WBS, estimates, risks, team, execution)
    into a publication-grade, downloadable PDF report with strict tenant isolation.
    """
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied.",
        )

    try:
        report = ReportGeneratorService.generate_delivery_report(
            db=db,
            tenant_id=current_user.tenant_id,
            project_id=project_id,
            generated_by_name=current_user.email,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

    return ReportSummaryResponse(
        id=report.id,
        tenant_id=report.tenant_id,
        project_id=report.project_id,
        title=report.title,
        report_type=report.report_type,
        baseline_version=report.baseline_version,
        file_size_bytes=report.file_size_bytes,
        generated_by=report.generated_by,
        created_at=report.created_at,
    )


@router.get("/{project_id}", response_model=List[ReportSummaryResponse])
def list_project_reports(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all generated report records for a project with tenant isolation."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == current_user.tenant_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied.",
        )

    reports = (
        db.query(ProjectReport)
        .filter(ProjectReport.tenant_id == current_user.tenant_id, ProjectReport.project_id == project_id)
        .order_by(ProjectReport.created_at.desc())
        .all()
    )
    return [
        ReportSummaryResponse(
            id=r.id,
            tenant_id=r.tenant_id,
            project_id=r.project_id,
            title=r.title,
            report_type=r.report_type,
            baseline_version=r.baseline_version,
            file_size_bytes=r.file_size_bytes,
            generated_by=r.generated_by,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get("/{report_id}/download")
def download_pdf_report(
    report_id: str,
    current_user: AuthenticatedUser = Depends(get_auth_for_download),
    db: Session = Depends(get_db),
):
    """Streams the generated PDF report artifact to the client for download with tenant isolation."""
    report = (
        db.query(ProjectReport)
        .filter(ProjectReport.id == report_id, ProjectReport.tenant_id == current_user.tenant_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report record not found or access denied.")

    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF artifact file is missing from server storage.")

    safe_filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", os.path.basename(report.file_path))
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=safe_filename,
    )
