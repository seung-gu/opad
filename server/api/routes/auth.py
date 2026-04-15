"""Authentication routes (register, login)."""

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.dependencies import get_user_repo
from api.models import UserResponse
from api.security import create_access_token, get_current_user_required
from domain.model.errors import DomainError, DuplicateError, ValidationError
from port.user_repository import UserRepository
from services import auth_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    """Register a new user."""
    try:
        user = auth_service.register(repo, request.email, request.password, request.name)
    except DuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    token = create_access_token(user.id)
    user_response = {k: v for k, v in asdict(user).items() if k != 'password_hash'}

    logger.info("User registered", extra={"userId": user.id, "email": request.email})
    return AuthResponse(token=token, user=user_response)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, repo: UserRepository = Depends(get_user_repo)):
    """Login user and return JWT token."""
    try:
        user = auth_service.authenticate(repo, request.email, request.password)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(user.id)
    user_response = {k: v for k, v in asdict(user).items() if k != 'password_hash'}

    logger.info("User logged in", extra={"userId": user.id, "email": request.email})
    return AuthResponse(token=token, user=user_response)


@router.get("/me")
async def get_me(current_user: UserResponse = Depends(get_current_user_required)):
    """Get current authenticated user info."""
    user_dict = current_user.model_dump()
    user_response = {k: v for k, v in user_dict.items() if k != 'password_hash'}
    return user_response
