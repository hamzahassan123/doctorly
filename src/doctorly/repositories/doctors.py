from sqlalchemy import select
from sqlalchemy.orm import Session

from doctorly.models import Doctor


class DoctorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_active(self) -> list[Doctor]:
        return list(
            self.session.scalars(
                select(Doctor)
                .where(Doctor.is_active.is_(True))
                .order_by(Doctor.specialty, Doctor.display_name)
            ).all()
        )
