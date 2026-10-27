from pydantic import model_validator

from doctorly.models import AppointmentStatus
from doctorly.schemas.appointments import AppointmentRead
from doctorly.schemas.catalog import PatientProfileRead
from doctorly.schemas.common import ApiSchema


class AppointmentStaffUpdate(ApiSchema):
    status: AppointmentStatus | None = None
    is_flagged: bool | None = None

    @model_validator(mode="after")
    def require_a_change(self) -> "AppointmentStaffUpdate":
        if self.status is None and self.is_flagged is None:
            raise ValueError("Provide a status or is_flagged update")
        return self


class StaffAppointmentRead(AppointmentRead):
    patient_profile: PatientProfileRead
