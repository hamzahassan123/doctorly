from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from doctorly.db.session import get_session
from doctorly.models import Doctor
from doctorly.models.entities import AvailabilitySlot
from doctorly.repositories.appointments import AppointmentRepository
from doctorly.repositories.doctors import DoctorRepository
from doctorly.schemas.catalog import AvailabilitySlotRead, DoctorRead

router = APIRouter(tags=["doctors"])


@router.get("/doctors", response_model=list[DoctorRead])
def list_doctors(session: Session = Depends(get_session)) -> list[Doctor]:
    return DoctorRepository(session).list_active()


@router.get("/slots", response_model=list[AvailabilitySlotRead])
def list_available_slots(
    doctor_id: UUID | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[AvailabilitySlot]:
    return AppointmentRepository(session).get_available_slots(doctor_id=doctor_id)
