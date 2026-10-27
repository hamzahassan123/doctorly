from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from doctorly.core.security import require_staff
from doctorly.db.session import get_session
from doctorly.models import Appointment, User
from doctorly.repositories.appointments import AppointmentRepository
from doctorly.schemas.staff import AppointmentStaffUpdate, StaffAppointmentRead
from doctorly.services.appointments import AppointmentManagementService
from doctorly.services.errors import InvalidAppointmentTransitionError

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/appointments", response_model=list[StaffAppointmentRead])
def list_appointments(
    staff: User = Depends(require_staff),
    session: Session = Depends(get_session),
) -> list[Appointment]:
    return AppointmentRepository(session).get_all()


@router.patch(
    "/appointments/{appointment_id}",
    response_model=StaffAppointmentRead,
)
def update_appointment(
    appointment_id: UUID,
    changes: AppointmentStaffUpdate,
    staff: User = Depends(require_staff),
    session: Session = Depends(get_session),
) -> Appointment:
    try:
        appointment = AppointmentManagementService(session).update(
            appointment_id,
            staff,
            changes,
        )
    except InvalidAppointmentTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested appointment status transition is not allowed",
        ) from exc
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    return appointment
