"""Authentication routes (register, login)."""

import logging
import re
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
import sys
from pathlib import Path

# Add src to path
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from api.middleware.auth import create_access_token
from utils.mongodb import get_user, create_user
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, ""


class RegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response model for authentication."""
    token: str
    user: dict


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new user.
    
    Args:
        request: Registration request with email, password, name
        
    Returns:
        JWT token and user info
        
    Raises:
        HTTPException: 400 if email already exists or validation fails
    """
    # Check if user already exists
    existing_user = get_user(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    is_valid, error_msg = validate_password(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Hash password
    password_hash = get_password_hash(request.password)
    
    # Create user
    user = create_user(
        email=request.email,
        password_hash=password_hash,
        name=request.name
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Generate JWT token
    token = create_access_token(user['id'])
    
    # Remove password_hash from response
    user_response = {k: v for k, v in user.items() if k != 'password_hash'}
    
    logger.info("User registered", extra={"userId": user['id'], "email": request.email})
    
    return AuthResponse(token=token, user=user_response)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user and return JWT token.
    
    Args:
        request: Login request with email and password
        
    Returns:
        JWT token and user info
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Get user by email
    user = get_user(request.email)
    if not user:
        # Don't reveal if email exists (security best practice)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last_login (optional - can be done in background)
    # For now, we'll skip this to keep it simple
    
    # Generate JWT token
    token = create_access_token(user['id'])
    
    # Remove password_hash from response
    user_response = {k: v for k, v in user.items() if k != 'password_hash'}
    
    logger.info("User logged in", extra={"userId": user['id'], "email": request.email})
    
    return AuthResponse(token=token, user=user_response)
