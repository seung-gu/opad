"""Authentication routes (register, login)."""

import logging
import re
from dataclasses import asdict

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.dependencies import get_user_repo
from api.models import UserResponse
from api.security import create_access_token, get_current_user_required
from domain.model.user import User
from port.user_repository import UserRepository


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# bcrypt configuration
# Using 12 rounds (2^12 = 4096 iterations) for secure password hashing
BCRYPT_ROUNDS = 12


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password (string format)

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password as string
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


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
async def register(request: RegisterRequest, repo: UserRepository = Depends(get_user_repo)):
    """Register a new user.

    Args:
        request: Registration request with email, password, name

    Returns:
        JWT token and user info

    Raises:
        HTTPException: 409 Conflict if email already exists, 400 Bad Request if validation fails
    """
    # Check if user already exists
    existing_user = repo.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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
    user: User | None = repo.create(
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
    token = create_access_token(user.id)
    
    # Remove password_hash from response
    user_response = {k: v for k, v in asdict(user).items() if k != 'password_hash'}
    
    logger.info("User registered", extra={"userId": user.id, "email": request.email})
    
    return AuthResponse(token=token, user=user_response)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, repo: UserRepository = Depends(get_user_repo)):
    """Login user and return JWT token.
    
    Args:
        request: Login request with email and password
        
    Returns:
        JWT token and user info
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Get user by email
    user = repo.get_by_email(request.email)
    if not user:
        # Don't reveal if email exists (security best practice)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Update last_login timestamp
    # Note: We don't check the return value - login succeeds even if update fails
    # This is intentional to prevent login failures due to database issues
    repo.update_last_login(user.id)

    # Generate JWT token
    token = create_access_token(user.id)
    
    # Remove password_hash from response
    user_response = {k: v for k, v in asdict(user).items() if k != 'password_hash'}
    
    logger.info("User logged in", extra={"userId": user.id, "email": request.email})

    return AuthResponse(token=token, user=user_response)


@router.get("/me")
async def get_me(current_user: UserResponse = Depends(get_current_user_required)):
    """Get current authenticated user info.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        User info (without password_hash)

    Raises:
        HTTPException: 401 if not authenticated
    """
    # Convert User model to dict and remove password_hash
    user_dict = current_user.model_dump()
    user_response = {k: v for k, v in user_dict.items() if k != 'password_hash'}

    return user_response
