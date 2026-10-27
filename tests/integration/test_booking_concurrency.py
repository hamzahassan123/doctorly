import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from doctorly.models import (
    Appointment,
    Base,
    AvailabilitySlot,
    Doctor,
    PatientProfile,
    User,
    UserRole,
)
from doctorly.repositories.appointments import AppointmentRepository
from doctorly.services.booking import BookingService
from doctorly.services.errors import SlotUnavailableError

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="Set TEST_DATABASE_URL to run PostgreSQL integration tests",
)


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")

    admin_engine = create_engine(database_url, pool_pre_ping=True)
    schema_name = f"doctorly_test_{uuid4().hex}"
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    test_engine = admin_engine.execution_options(
        schema_translate_map={None: schema_name}
    )
    try:
        Base.metadata.create_all(test_engine)
        yield test_engine
    finally:
        test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        admin_engine.dispose()


def test_only_one_concurrent_booking_for_a_slot_succeeds(
    postgres_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = sessionmaker(
        bind=postgres_engine,
        expire_on_commit=False,
    )
    with session_factory() as session:
        doctor = Doctor(display_name="Concurrent Test Doctor", specialty="Cardiology")
        patients = [
            PatientProfile(
                user=User(
                    email=f"concurrent-{index}-{uuid4().hex}@example.test",
                    password_hash="test-hash",
                    role=UserRole.PATIENT,
                ),
                full_name=f"Concurrent Patient {index}",
            )
            for index in range(2)
        ]
        starts_at = datetime.now(UTC) + timedelta(days=3)
        slot = AvailabilitySlot(
            doctor=doctor,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
        )
        session.add_all([*patients, slot])
        session.commit()
        patient_ids = [patient.user_id for patient in patients]
        slot_id = slot.id

    barrier = Barrier(2)
    original_check_conflicts = AppointmentRepository.check_conflicts

    def synchronize_conflict_checks(
        repository: AppointmentRepository,
        checked_slot_id,
    ) -> bool:
        conflicts = original_check_conflicts(repository, checked_slot_id)
        barrier.wait(timeout=15)
        return conflicts

    monkeypatch.setattr(
        AppointmentRepository,
        "check_conflicts",
        synchronize_conflict_checks,
    )

    def attempt_booking(patient_id):
        with session_factory() as session:
            patient = session.get(User, patient_id)
            assert patient is not None
            try:
                BookingService(session).book(patient, slot_id)
                return "booked"
            except SlotUnavailableError:
                return "unavailable"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt_booking, patient_ids))

    assert sorted(outcomes) == ["booked", "unavailable"]
    with session_factory() as session:
        appointments = session.query(Appointment).all()
        assert len(appointments) == 1
