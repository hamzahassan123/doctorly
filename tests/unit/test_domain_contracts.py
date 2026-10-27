from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from doctorly.models import (
    Appointment,
    AppointmentStatus,
    AvailabilitySlot,
    Base,
    Doctor,
    PatientProfile,
    User,
    UserRole,
)
from doctorly.schemas import AppointmentCreate


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_patient_and_slot(session: Session) -> tuple[PatientProfile, AvailabilitySlot]:
    patient_user = User(
        email="patient@example.test",
        password_hash="test-hash",
        role=UserRole.PATIENT,
    )
    patient = PatientProfile(user=patient_user, full_name="Test Patient")
    doctor = Doctor(display_name="Test Doctor", specialty="Cardiology")
    starts_at = datetime.now(UTC) + timedelta(days=1)
    slot = AvailabilitySlot(
        doctor=doctor,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
    )
    session.add_all([patient, slot])
    session.flush()
    return patient, slot


def test_booking_create_contract_accepts_slot_id_only() -> None:
    slot_id = uuid4()
    request = AppointmentCreate(availability_slot_id=slot_id)

    assert request.availability_slot_id == slot_id

    with pytest.raises(ValidationError):
        AppointmentCreate(
            availability_slot_id=slot_id,
            patient_id=uuid4(),
        )


def test_active_appointments_cannot_double_book_a_slot(session: Session) -> None:
    patient, slot = add_patient_and_slot(session)
    session.add(
        Appointment(
            patient_profile=patient,
            availability_slot=slot,
            status=AppointmentStatus.CONFIRMED,
        )
    )
    session.commit()

    session.add(
        Appointment(
            patient_profile=patient,
            availability_slot=slot,
            status=AppointmentStatus.PENDING_APPROVAL,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    existing = session.scalar(select(Appointment))
    assert existing is not None
    existing.status = AppointmentStatus.CANCELLED
    session.commit()
    session.add(
        Appointment(
            patient_profile=patient,
            availability_slot=slot,
            status=AppointmentStatus.CONFIRMED,
        )
    )
    session.commit()

    assert len(session.scalars(select(Appointment)).all()) == 2
