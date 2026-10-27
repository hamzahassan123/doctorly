from uuid import UUID

from sqlalchemy.orm import Session

from doctorly.models import Appointment, AppointmentStatus, AuditLog, User
from doctorly.repositories.appointments import AppointmentRepository
from doctorly.schemas.staff import AppointmentStaffUpdate
from doctorly.services.errors import InvalidAppointmentTransitionError

_ALLOWED_TRANSITIONS = {
    AppointmentStatus.PENDING_APPROVAL: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.CANCELLED,
        AppointmentStatus.COMPLETED,
    },
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.COMPLETED: set(),
}


class AppointmentManagementService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.appointments = AppointmentRepository(session)

    def update(
        self,
        appointment_id: UUID,
        actor: User,
        changes: AppointmentStaffUpdate,
    ) -> Appointment | None:
        appointment = self.appointments.get_by_id(appointment_id)
        if appointment is None:
            return None

        audit_details: dict[str, str | bool] = {}
        if changes.status is not None and changes.status != appointment.status:
            allowed = _ALLOWED_TRANSITIONS[appointment.status]
            if changes.status not in allowed:
                raise InvalidAppointmentTransitionError()
            audit_details["status"] = changes.status.value
            appointment.status = changes.status

        if changes.is_flagged is not None and changes.is_flagged != appointment.is_flagged:
            audit_details["is_flagged"] = changes.is_flagged
            appointment.is_flagged = changes.is_flagged

        if audit_details:
            self.session.add(
                AuditLog(
                    actor_user_id=actor.id,
                    target_type="appointment",
                    target_id=appointment.id,
                    action="staff_update",
                    details=audit_details,
                )
            )
            self.session.commit()
        return appointment
