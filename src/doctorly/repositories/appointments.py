from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from doctorly.models import (
    Appointment,
    AppointmentStatus,
    AvailabilitySlot,
    Doctor,
)

ACTIVE_STATUSES = (
    AppointmentStatus.PENDING_APPROVAL,
    AppointmentStatus.CONFIRMED,
)


class AppointmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_available_slots(
        self,
        *,
        doctor_id: UUID | None = None,
        now: datetime | None = None,
    ) -> list[AvailabilitySlot]:
        current_time = now or datetime.now(UTC)
        occupied = (
            select(Appointment.id)
            .where(
                Appointment.availability_slot_id == AvailabilitySlot.id,
                Appointment.status.in_(ACTIVE_STATUSES),
            )
            .exists()
        )
        query = (
            select(AvailabilitySlot)
            .join(Doctor)
            .where(
                Doctor.is_active.is_(True),
                AvailabilitySlot.starts_at > current_time,
                ~occupied,
            )
            .order_by(AvailabilitySlot.starts_at)
        )
        if doctor_id is not None:
            query = query.where(AvailabilitySlot.doctor_id == doctor_id)
        return list(self.session.scalars(query).all())

    def get_available_slot(
        self, slot_id: UUID, *, now: datetime | None = None
    ) -> AvailabilitySlot | None:
        current_time = now or datetime.now(UTC)
        occupied = (
            select(Appointment.id)
            .where(
                Appointment.availability_slot_id == AvailabilitySlot.id,
                Appointment.status.in_(ACTIVE_STATUSES),
            )
            .exists()
        )
        return self.session.scalar(
            select(AvailabilitySlot)
            .join(Doctor)
            .where(
                AvailabilitySlot.id == slot_id,
                AvailabilitySlot.starts_at > current_time,
                Doctor.is_active.is_(True),
                ~occupied,
            )
        )

    def check_conflicts(self, slot_id: UUID) -> bool:
        return (
            self.session.scalar(
                select(
                    select(Appointment.id)
                    .where(
                        Appointment.availability_slot_id == slot_id,
                        Appointment.status.in_(ACTIVE_STATUSES),
                    )
                    .exists()
                )
            )
            is True
        )

    def create_appointment(self, patient_id: UUID, slot_id: UUID) -> Appointment:
        appointment = Appointment(
            patient_id=patient_id,
            availability_slot_id=slot_id,
            status=AppointmentStatus.CONFIRMED,
        )
        self.session.add(appointment)
        return appointment

    def get_for_patient(self, patient_id: UUID) -> list[Appointment]:
        return list(
            self.session.scalars(
                select(Appointment)
                .options(selectinload(Appointment.availability_slot))
                .where(Appointment.patient_id == patient_id)
                .order_by(Appointment.created_at.desc())
            ).all()
        )

    def get_all(self) -> list[Appointment]:
        return list(
            self.session.scalars(
                select(Appointment)
                .options(
                    selectinload(Appointment.availability_slot),
                    selectinload(Appointment.patient_profile),
                )
                .order_by(Appointment.created_at.desc())
            ).all()
        )

    def get_by_id(self, appointment_id: UUID) -> Appointment | None:
        return self.session.scalar(
            select(Appointment)
            .options(
                selectinload(Appointment.availability_slot),
                selectinload(Appointment.patient_profile),
            )
            .where(Appointment.id == appointment_id)
        )
