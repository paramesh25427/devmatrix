from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user, AuthenticatedUser
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str
    tenant_name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserResponse


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates user with email and password, returning an expiring JWT token."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Please contact your tenant administrator.",
        )

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    tenant_name = tenant.name if tenant else "Default Organization"

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
    )

    return LoginResponse(
        access_token=token,
        token_type="Bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_name=tenant_name,
        ),
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves authenticated user profile and tenant details."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    tenant_name = tenant.name if tenant else "Default Organization"

    user = db.query(User).filter(User.id == current_user.id).first()
    full_name = user.full_name if user else "Authenticated User"

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=full_name,
        role=current_user.role,
        tenant_id=current_user.tenant_id,
        tenant_name=tenant_name,
    )


@router.post("/logout")
def logout(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Logs out user; client clears access token from local storage."""
    return {"message": "Successfully logged out."}
