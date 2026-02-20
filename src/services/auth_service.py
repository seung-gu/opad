"""Auth service — registration and authentication business logic.

Pure business logic with no HTTP dependencies.
Raises domain errors that route handlers map to HTTP status codes.
"""

import re

import bcrypt

from domain.model.errors import DomainError, DuplicateError, ValidationError
from domain.model.user import User
from port.user_repository import UserRepository

BCRYPT_ROUNDS = 12


def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValidationError("Password must contain at least one number")


def register(repo: UserRepository, email: str, password: str, name: str) -> User:
    """Register a new user.

    Returns the created User domain object.

    Raises:
        DuplicateError: email already registered
        ValidationError: password does not meet strength requirements
    """
    if repo.get_by_email(email):
        raise DuplicateError("Email already registered")

    _validate_password(password)
    password_hash = _hash_password(password)

    user = repo.create(email=email, password_hash=password_hash, name=name)
    if not user:
        raise DomainError("Failed to create user")
    return user


def authenticate(repo: UserRepository, email: str, password: str) -> User:
    """Authenticate a user by email and password.

    Returns the authenticated User domain object.
    Uses constant-time comparison and doesn't reveal whether email exists.

    Raises:
        ValidationError: invalid credentials (deliberately vague)
    """
    user = repo.get_by_email(email)
    if not user or not _verify_password(password, user.password_hash):
        raise ValidationError("Invalid email or password")

    repo.update_last_login(user.id)
    return user
