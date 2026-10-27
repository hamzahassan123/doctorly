from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from doctorly.core.config import get_settings
from doctorly.db.session import get_session
from doctorly.models import User, UserRole
from doctorly.repositories.users import UserRepository

password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


class SecurityConfigurationError(RuntimeError):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def _jwt_secret() -> str:
    secret = get_settings().jwt_secret_key
    if secret is None or len(secret.encode("utf-8")) < 32:
        raise SecurityConfigurationError(
            "DOCTORLY_JWT_SECRET_KEY must contain at least 32 bytes"
        )
    return secret


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=get_settings().jwt_access_token_minutes)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": expires_at,
            "iss": "doctorly",
        },
        _jwt_secret(),
        algorithm="HS256",
    )


def decode_access_token(token: str) -> UUID:
    claims = jwt.decode(
        token,
        _jwt_secret(),
        algorithms=["HS256"],
        issuer="doctorly",
        options={"require": ["exp", "iat", "iss", "sub"]},
    )
    return UUID(claims["sub"])


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = decode_access_token(credentials.credentials)
    except SecurityConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )
    return user


def require_patient(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient access required",
        )
    return user
