import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from doctorly.core.config import get_settings
from doctorly.core.security import hash_password
from doctorly.db.session import get_session
from doctorly.main import app
from doctorly.models import (
    Appointment,
    AppointmentStatus,
    AuditLog,
    AvailabilitySlot,
    Base,
    Doctor,
    User,
    UserRole,
)


@pytest.fixture
def api_engine() -> Iterator:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def api_client(api_engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[AsyncClient]:
    monkeypatch.setattr(get_settings(), "jwt_secret_key", "test-secret-" + "x" * 40)

    def override_session() -> Iterator[Session]:
        with Session(api_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    )
    yield client
    app.dependency_overrides.pop(get_session, None)
    asyncio.run(client.aclose())


def add_future_slot(api_engine) -> tuple[UUID, UUID]:
    with Session(api_engine) as session:
        doctor = Doctor(display_name="Dr Test", specialty="Cardiology")
        starts_at = datetime.now(UTC) + timedelta(days=2)
        slot = AvailabilitySlot(
            doctor=doctor,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
        )
        session.add(slot)
        session.commit()
        return doctor.id, slot.id


def test_patient_auth_booking_ownership_and_staff_access(
    api_client: AsyncClient,
    api_engine,
) -> None:
    async def workflow() -> None:
        doctor_id, slot_id = add_future_slot(api_engine)
        doctors = await api_client.get("/doctors")
        slots = await api_client.get("/slots", params={"doctor_id": str(doctor_id)})
        assert doctors.status_code == 200
        assert len(doctors.json()) == 1
        assert slots.status_code == 200
        assert [slot["id"] for slot in slots.json()] == [str(slot_id)]

        registration = await api_client.post(
            "/register",
            json={
                "email": "patient@example.com",
                "password": "secure-test-password-1",
                "full_name": "Test Patient",
            },
        )
        assert registration.status_code == 201
        assert registration.json()["role"] == "patient"
        assert "password_hash" not in registration.json()

        login = await api_client.post(
            "/login",
            json={
                "email": "PATIENT@example.com",
                "password": "secure-test-password-1",
            },
        )
        assert login.status_code == 200
        patient_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        current_user = await api_client.get("/me", headers=patient_headers)
        assert current_user.status_code == 200
        assert current_user.json()["email"] == "patient@example.com"

        booking = await api_client.post(
            "/appointments",
            json={"availability_slot_id": str(slot_id)},
            headers=patient_headers,
        )
        assert booking.status_code == 201
        assert booking.json()["patient_id"] == registration.json()["id"]
        assert booking.json()["status"] == "confirmed"

        own_appointments = await api_client.get(
            "/appointments",
            headers=patient_headers,
        )
        assert own_appointments.status_code == 200
        assert len(own_appointments.json()) == 1

        duplicate_booking = await api_client.post(
            "/appointments",
            json={"availability_slot_id": str(slot_id)},
            headers=patient_headers,
        )
        assert duplicate_booking.status_code == 409

        patient_cannot_view_staff_queue = await api_client.get(
            "/staff/appointments",
            headers=patient_headers,
        )
        assert patient_cannot_view_staff_queue.status_code == 403

        with Session(api_engine) as session:
            staff = User(
                email="staff@example.com",
                password_hash=hash_password("secure-test-password-2"),
                role=UserRole.STAFF,
            )
            session.add(staff)
            session.commit()
            staff_id = staff.id

        staff_login = await api_client.post(
            "/login",
            json={
                "email": "staff@example.com",
                "password": "secure-test-password-2",
            },
        )
        assert staff_login.status_code == 200
        staff_headers = {
            "Authorization": f"Bearer {staff_login.json()['access_token']}"
        }

        staff_appointments = await api_client.get(
            "/staff/appointments",
            headers=staff_headers,
        )
        assert staff_appointments.status_code == 200
        appointment_id = staff_appointments.json()[0]["id"]

        update = await api_client.patch(
            f"/staff/appointments/{appointment_id}",
            json={"is_flagged": True},
            headers=staff_headers,
        )
        assert update.status_code == 200
        assert update.json()["is_flagged"] is True
        assert update.json()["patient_profile"]["user_id"] == registration.json()["id"]

        cancel = await api_client.patch(
            f"/staff/appointments/{appointment_id}",
            json={"status": "cancelled"},
            headers=staff_headers,
        )
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        invalid_transition = await api_client.patch(
            f"/staff/appointments/{appointment_id}",
            json={"status": "confirmed"},
            headers=staff_headers,
        )
        assert invalid_transition.status_code == 409

        released_slots = await api_client.get(
            "/slots",
            params={"doctor_id": str(doctor_id)},
        )
        assert [slot["id"] for slot in released_slots.json()] == [str(slot_id)]

        with Session(api_engine) as session:
            appointment = session.scalar(select(Appointment))
            assert appointment is not None
            assert appointment.status == AppointmentStatus.CANCELLED
            assert appointment.is_flagged is True
            assert len(session.scalars(select(AuditLog)).all()) == 2

        assert staff_id != UUID(registration.json()["id"])

    asyncio.run(workflow())


def test_registration_cannot_assign_staff_role(api_client: AsyncClient) -> None:
    response = asyncio.run(
        api_client.post(
            "/register",
            json={
                "email": "attacker@example.com",
                "password": "secure-test-password-3",
                "full_name": "Not Staff",
                "role": "staff",
            },
        )
    )

    assert response.status_code == 422


def test_duplicate_registration_and_invalid_password_are_rejected(
    api_client: AsyncClient,
) -> None:
    async def workflow() -> None:
        payload = {
            "email": "duplicate@example.com",
            "password": "secure-test-password-4",
            "full_name": "Duplicate Patient",
        }
        first = await api_client.post("/register", json=payload)
        duplicate = await api_client.post("/register", json=payload)
        invalid_login = await api_client.post(
            "/login",
            json={
                "email": payload["email"],
                "password": "wrong-password",
            },
        )
        assert first.status_code == 201
        assert duplicate.status_code == 409
        assert invalid_login.status_code == 401

    asyncio.run(workflow())


def test_missing_bearer_token_is_rejected(api_client: AsyncClient) -> None:
    response = asyncio.run(api_client.get("/appointments"))

    assert response.status_code == 401
