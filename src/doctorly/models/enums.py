from enum import StrEnum


class UserRole(StrEnum):
    PATIENT = "patient"
    STAFF = "staff"


class AppointmentStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class IngestionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

