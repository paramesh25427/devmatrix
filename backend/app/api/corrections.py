import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles, AuthenticatedUser
from app.models.correction import CorrectionRequest

router = APIRouter(prefix="/api/corrections", tags=["corrections"])


class CorrectionSubmitRequest(BaseModel):
    record_type: str  # task_hours, metric, blocker
    record_id: str
    reason: str


class CorrectionReviewRequest(BaseModel):
    status: str  # approved, rejected
    manager_notes: Optional[str] = None


class CorrectionResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    user_name: str
    record_type: str
    record_id: str
    reason: str
    status: str
    manager_notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]


@router.post("", response_model=CorrectionResponse, status_code=status.HTTP_201_CREATED)
def submit_correction_request(
    payload: CorrectionSubmitRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Empowers contributors and project members to formally challenge or request
    corrections to recorded work logs, task hours, or delivery metrics.
    """
    req_id = str(uuid.uuid4())
    req = CorrectionRequest(
        id=req_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_name=current_user.email,
        record_type=payload.record_type,
        record_id=payload.record_id,
        reason=payload.reason,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return CorrectionResponse(
        id=req.id,
        tenant_id=req.tenant_id,
        user_id=req.user_id,
        user_name=req.user_name,
        record_type=req.record_type,
        record_id=req.record_id,
        reason=req.reason,
        status=req.status,
        manager_notes=req.manager_notes,
        created_at=req.created_at,
        resolved_at=req.resolved_at,
    )


@router.get("", response_model=List[CorrectionResponse])
def list_correction_requests(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves correction requests within tenant scope."""
    query = db.query(CorrectionRequest).filter(CorrectionRequest.tenant_id == current_user.tenant_id)
    if current_user.role == "contributor":
        query = query.filter(CorrectionRequest.user_id == current_user.id)
    requests = query.order_by(CorrectionRequest.created_at.desc()).all()

    return [
        CorrectionResponse(
            id=r.id,
            tenant_id=r.tenant_id,
            user_id=r.user_id,
            user_name=r.user_name,
            record_type=r.record_type,
            record_id=r.record_id,
            reason=r.reason,
            status=r.status,
            manager_notes=r.manager_notes,
            created_at=r.created_at,
            resolved_at=r.resolved_at,
        )
        for r in requests
    ]


@router.put("/{request_id}", response_model=CorrectionResponse)
def resolve_correction_request(
    request_id: str,
    payload: CorrectionReviewRequest,
    current_user: AuthenticatedUser = Depends(require_roles(["delivery_manager", "tenant_admin"])),
    db: Session = Depends(get_db),
):
    """Delivery Manager reviews and resolves a contributor correction challenge."""
    req = (
        db.query(CorrectionRequest)
        .filter(CorrectionRequest.id == request_id, CorrectionRequest.tenant_id == current_user.tenant_id)
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Correction request not found.")

    req.status = payload.status
    req.manager_notes = payload.manager_notes
    req.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(req)

    return CorrectionResponse(
        id=req.id,
        tenant_id=req.tenant_id,
        user_id=req.user_id,
        user_name=req.user_name,
        record_type=req.record_type,
        record_id=req.record_id,
        reason=req.reason,
        status=req.status,
        manager_notes=req.manager_notes,
        created_at=req.created_at,
        resolved_at=req.resolved_at,
    )
