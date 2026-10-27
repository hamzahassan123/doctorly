from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from doctorly.core.security import (
    create_access_token,
    hash_password,
    password_hasher,
    verify_password,
)
from doctorly.models import User
from doctorly.repositories.users import UserRepository
from doctorly.schemas.auth import UserRegister
from doctorly.services.errors import DuplicateEmailError, InvalidCredentialsError

_DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-real-user-password")


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def register_patient(self, request: UserRegister) -> User:
        email = str(request.email).strip().lower()
        if self.users.get_by_email(email) is not None:
            raise DuplicateEmailError()

        try:
            user = self.users.create_patient(
                email=email,
                password_hash=hash_password(request.password.get_secret_value()),
                full_name=request.full_name,
                phone_number=request.phone_number,
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            if _is_duplicate_email(exc):
                raise DuplicateEmailError from exc
            raise
        return user

    def authenticate(self, email: str, password: str) -> tuple[User, str]:
        user = self.users.get_by_email(email)
        stored_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        password_matches = verify_password(password, stored_hash)
        if user is None or not user.is_active or not password_matches:
            raise InvalidCredentialsError()
        return user, create_access_token(user.id)


def _is_duplicate_email(error: IntegrityError) -> bool:
    constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if constraint_name == "uq_users_email":
        return True
    return "users.email" in str(error.orig).lower()
