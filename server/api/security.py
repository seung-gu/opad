"""JWT authentication and security dependencies."""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from api.dependencies import get_user_repo
from api.models import UserResponse
from domain.model.user import User
from port.user_repository import UserRepository

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY environment variable is required. "
        "Generate a secure key with: openssl rand -hex 32"
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7

security = HTTPBearer(auto_error=False)


def _to_response(user: User) -> UserResponse:
    """Convert domain User to API UserResponse."""
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        provider=user.provider,
    )


def create_access_token(user_id: str) -> str:
    """Create JWT access token for user."""
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and extract user_id."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError as e:
        logger.debug(f"JWT verification failed: {e}")
        return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_repo: UserRepository = Depends(get_user_repo),
) -> Optional[UserResponse]:
    """Get current authenticated user (optional). Returns None if no token."""
    if not credentials:
        return None

    user_id = verify_token(credentials.credentials)
    if not user_id:
        return None

    user = user_repo.get_by_id(user_id)
    if not user:
        return None

    return _to_response(user)


def get_current_user_required(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserResponse:
    """Get current authenticated user (required). Raises 401 if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _to_response(user)
