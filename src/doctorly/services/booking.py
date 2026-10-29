import asyncio
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from doctorly.models import Appointment, User, UserRole
from doctorly.repositories.appointments import AppointmentRepository
from doctorly.services.email import send_booking_confirmation_email
from doctorly.services.errors import SlotUnavailableError


def _trigger_booking_email(patient: User, appointment: Appointment) -> None:
    slot = appointment.availability_slot
    if slot is None or not patient.email:
        return

    async def _send() -> None:
        await send_booking_confirmation_email(
            recipient=patient.email,
            summary=f"Appointment with {slot.doctor.display_name}",
            start=slot.starts_at,
            end=slot.ends_at,
            location=slot.doctor.display_name,
            description=f"Appointment with Dr. {slot.doctor.display_name}",
            uid=str(appointment.id),
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_send())
        return

    loop.create_task(_send())


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
        _trigger_booking_email(patient, appointment)
        return appointment


def _is_active_slot_conflict(error: IntegrityError) -> bool:
    constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    if constraint_name == "uq_appointments_active_slot":
        return True
    return "appointments.availability_slot_id" in str(error.orig).lower()
