from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime

from doctorly.models.enums import AppointmentStatus
from doctorly.schemas.catalog import AvailabilitySlotRead
from doctorly.schemas.common import ApiSchema


class AppointmentCreate(ApiSchema):
    availability_slot_id: UUID


class AppointmentRead(ApiSchema):
    id: UUID
    patient_id: UUID
    availability_slot_id: UUID
    status: AppointmentStatus
    is_flagged: bool
    created_at: datetime
    updated_at: datetime
    availability_slot: AvailabilitySlotRead
