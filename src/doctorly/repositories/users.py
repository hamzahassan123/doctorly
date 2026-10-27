from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from doctorly.models import PatientProfile, User, UserRole


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(
            select(User).where(User.email == email.strip().lower())
        )

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def create_patient(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        phone_number: str | None,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            role=UserRole.PATIENT,
        )
        user.patient_profile = PatientProfile(
            full_name=full_name,
            phone_number=phone_number,
        )
        self.session.add(user)
        self.session.flush()
        return user
