from doctorly.schemas.appointments import AppointmentCreate, AppointmentRead
from doctorly.schemas.auth import AccessTokenRead, LoginRequest, UserRead, UserRegister
from doctorly.schemas.catalog import (
    AvailabilitySlotRead,
    DoctorRead,
    PatientProfileRead,
)
from doctorly.schemas.common import ErrorResponse

__all__ = [
    "AppointmentCreate",
    "AppointmentRead",
    "AccessTokenRead",
    "AvailabilitySlotRead",
    "DoctorRead",
    "ErrorResponse",
    "LoginRequest",
    "PatientProfileRead",
    "UserRead",
    "UserRegister",
]
