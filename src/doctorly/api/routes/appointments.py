from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from doctorly.core.security import require_patient
from doctorly.db.session import get_session
from doctorly.models import Appointment, User
from doctorly.repositories.appointments import AppointmentRepository
from doctorly.schemas.appointments import AppointmentCreate, AppointmentRead
from doctorly.services.booking import BookingService
from doctorly.services.errors import SlotUnavailableError

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post(
    "",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    request: AppointmentCreate,
    patient: User = Depends(require_patient),
    session: Session = Depends(get_session),
) -> Appointment:
    try:
        return BookingService(session).book(patient, request.availability_slot_id)
    except SlotUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested appointment slot is unavailable",
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A patient profile is required to book appointments",
        ) from exc


@router.get("", response_model=list[AppointmentRead])
def list_my_appointments(
    patient: User = Depends(require_patient),
    session: Session = Depends(get_session),
) -> list[Appointment]:
    return AppointmentRepository(session).get_for_patient(patient.id)
