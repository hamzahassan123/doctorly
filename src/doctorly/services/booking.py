from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from doctorly.models import Appointment, User, UserRole
from doctorly.repositories.appointments import AppointmentRepository
from doctorly.services.errors import SlotUnavailableError


class BookingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.appointments = AppointmentRepository(session)

    def book(self, patient: User, slot_id: UUID) -> Appointment:
        if patient.role != UserRole.PATIENT or patient.patient_profile is None:
            raise PermissionError("A patient profile is required to book an appointment")

        slot = self.appointments.get_available_slot(slot_id)
        if slot is None or self.appointments.check_conflicts(slot_id):
            raise SlotUnavailableError()

        appointment = self.appointments.create_appointment(patient.id, slot_id)
        appointment.availability_slot = slot
        try:
            self.session.flush()
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            if _is_active_slot_conflict(exc):
                raise SlotUnavailableError() from exc
            raise
        return appointment


def _is_active_slot_conflict(error: IntegrityError) -> bool:
    constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if constraint_name == "uq_appointments_active_slot":
        return True
    return "appointments.availability_slot_id" in str(error.orig).lower()
