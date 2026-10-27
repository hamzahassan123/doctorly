from datetime import date
from uuid import UUID

from pydantic import AwareDatetime

from doctorly.schemas.common import ApiSchema
# all are using for send data from backend to front-end

class PatientProfileRead(ApiSchema):
    user_id: UUID
    full_name: str
    date_of_birth: date | None
    phone_number: str | None


class DoctorRead(ApiSchema):
    id: UUID
    display_name: str
    specialty: str
    is_active: bool


class AvailabilitySlotRead(ApiSchema):
    id: UUID
    doctor_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
