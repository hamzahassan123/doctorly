from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from doctorly.core.config import get_settings
from doctorly.core.security import SecurityConfigurationError, get_current_user
from doctorly.db.session import get_session
from doctorly.models import User
from doctorly.schemas.auth import AccessTokenRead, LoginRequest, UserRead, UserRegister
from doctorly.services.auth import AuthService
from doctorly.services.errors import DuplicateEmailError, InvalidCredentialsError

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: UserRegister,
    session: Session = Depends(get_session),
) -> User:
    try:
        return AuthService(session).register_patient(request)
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc


@router.post("/login", response_model=AccessTokenRead)
def login(
    request: LoginRequest,
    session: Session = Depends(get_session),
) -> AccessTokenRead:
    try:
        _, token = AuthService(session).authenticate(
            str(request.email),
            request.password.get_secret_value(),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except SecurityConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc

    return AccessTokenRead(
        access_token=token,
        expires_in=get_settings().jwt_access_token_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user
