from datetime import datetime, timedelta, timezone
from typing import Optional, List
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    tenant_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generates an expiring JWT access token with user and tenant claims."""
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthenticatedUser:
    """Represents the authenticated user context for the request."""
    def __init__(self, id: str, email: str, role: str, tenant_id: str):
        self.id = id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id

    def has_role(self, allowed_roles: List[str]) -> bool:
        return self.role in allowed_roles


async def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Optional[AuthenticatedUser]:
    """Extracts authenticated user if bearer token is present; returns default demo user if not present."""
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        tenant_id = payload.get("tenant_id")
        if user_id and role and tenant_id:
            return AuthenticatedUser(id=user_id, email=email or "", role=role, tenant_id=tenant_id)
    return None


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """
    Enforces authentication.
    If no token is supplied, falls back to a development demo manager session
    when in development mode, ensuring smooth developer testing.
    """
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        tenant_id = payload.get("tenant_id")
        if user_id and role and tenant_id:
            return AuthenticatedUser(id=user_id, email=email or "", role=role, tenant_id=tenant_id)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(allowed_roles: List[str]):
    """Role-based authorization dependency guard."""
    async def role_checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}. Your role is '{current_user.role}'.",
            )
        return current_user
    return role_checker
