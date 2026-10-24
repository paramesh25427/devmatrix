import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, verify_db_connection
from app.core.security import get_current_user, require_roles, AuthenticatedUser, hash_password
from app.models.user import User
from app.models.tenant import Tenant
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserCreateAdminRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: str  # tenant_admin, delivery_manager, project_lead, contributor


class UserAdminResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class TenantConfigRequest(BaseModel):
    name: Optional[str] = None
    currency: Optional[str] = None
    default_contingency_pct: Optional[str] = None
    retention_days: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: str
    tenant_id: str
    user_email: Optional[str]
    action: str
    entity_type: str
    entity_id: str
    details: Optional[Dict[str, Any]]
    created_at: datetime


@router.get("/users", response_model=List[UserAdminResponse])
def list_users(
    current_user: AuthenticatedUser = Depends(require_roles(["tenant_admin", "delivery_manager"])),
    db: Session = Depends(get_db),
):
    """Lists all users registered within the tenant."""
    users = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id)
        .order_by(User.created_at.desc())
        .all()
    )
    return [
        UserAdminResponse(
            id=u.id,
            tenant_id=u.tenant_id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/users", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
def create_user_by_admin(
    payload: UserCreateAdminRequest,
    current_user: AuthenticatedUser = Depends(require_roles(["tenant_admin"])),
    db: Session = Depends(get_db),
):
    """Tenant Administrator creates a new team member and grants role."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    import uuid
    u_id = str(uuid.uuid4())
    user = User(
        id=u_id,
        tenant_id=current_user.tenant_id,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)

    db.add(
        AuditLog(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            user_email=current_user.email,
            action="user_created",
            entity_type="user",
            entity_id=u_id,
            details_json=json.dumps({"email": payload.email, "role": payload.role}),
        )
    )

    db.commit()
    db.refresh(user)

    return UserAdminResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/tenant")
def get_tenant_configuration(
    current_user: AuthenticatedUser = Depends(require_roles(["tenant_admin", "delivery_manager"])),
    db: Session = Depends(get_db),
):
    """Retrieves tenant configuration, rate cards, and retention parameters."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "currency": tenant.currency,
        "default_contingency_pct": float(tenant.default_contingency_pct),
        "retention_days": int(tenant.retention_days),
        "created_at": tenant.created_at.isoformat(),
    }


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    current_user: AuthenticatedUser = Depends(require_roles(["tenant_admin", "delivery_manager"])),
    db: Session = Depends(get_db),
):
    """Retrieves immutable audit trail records for compliance and governance."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == current_user.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        AuditLogResponse(
            id=log.id,
            tenant_id=log.tenant_id,
            user_email=log.user_email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=json.loads(log.details_json) if log.details_json else None,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/diagnostics")
def get_system_diagnostics(
    current_user: AuthenticatedUser = Depends(require_roles(["tenant_admin"])),
):
    """
    Returns sanitized non-secret operational diagnostics:
    Database connectivity, storage directories, and configured AI adapter status.
    Never exposes API keys or secrets.
    """
    db_ok = False
    try:
        db_ok = verify_db_connection()
    except Exception:
        db_ok = False

    return {
        "app_env": settings.app_env,
        "database": {
            "status": "connected" if db_ok else "disconnected",
            "type": "sqlite",
        },
        "storage": {
            "storage_dir_exists": os.path.exists(settings.storage_dir),
            "uploads_dir_exists": os.path.exists(settings.uploads_dir),
            "reports_dir_exists": os.path.exists(settings.reports_dir),
        },
        "ai_providers": {
            "gemini": {
                "enabled": settings.gemini_enabled,
                "configured": bool(settings.gemini_api_key),
                "model": settings.gemini_model,
            },
            "nvidia_nim": {
                "enabled": settings.nvidia_nim_enabled,
                "configured": bool(settings.nvidia_nim_api_key),
                "model": settings.nvidia_nim_model,
            },
            "grok": {
                "enabled": settings.grok_enabled,
                "configured": bool(settings.grok_api_key),
                "model": settings.grok_model,
            },
            "offline_deterministic_mock": {
                "enabled": True,
                "status": "active_standby",
            },
        },
    }
