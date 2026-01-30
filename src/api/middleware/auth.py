"""JWT authentication middleware and utilities."""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import sys
from pathlib import Path

# Add src to path
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from utils.mongodb import get_user_by_id
from api.models import User

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


def create_access_token(user_id: str) -> str:
    """Create JWT access token for user.
    
    Args:
        user_id: User ID to encode in token
        
    Returns:
        JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)
    payload = {
        "sub": user_id,  # Subject (user ID)
        "exp": expire,   # Expiration
        "iat": datetime.now(timezone.utc),  # Issued at
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and extract user_id.
    
    Args:
        token: JWT token string
        
    Returns:
        User ID if token is valid, None otherwise
    """
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current authenticated user from JWT token.
    
    This is an optional dependency - returns None if no token provided.
    Use this for endpoints that work with or without authentication.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    user_id = verify_token(credentials.credentials)
    if not user_id:
        return None
    
    user_dict = get_user_by_id(user_id)
    if not user_dict:
        return None
    
    return User(**user_dict)


def get_current_user_required(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Get current authenticated user from JWT token (required).
    
    This is a required dependency - raises 401 if no token or invalid.
    Use this for protected endpoints that require authentication.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User object
        
    Raises:
        HTTPException: 401 if authentication fails
    """
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
    
    user_dict = get_user_by_id(user_id)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(**user_dict)
