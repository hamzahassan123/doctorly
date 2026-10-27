from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from doctorly.core.types import UTCDateTime
from doctorly.models.base import Base
from doctorly.models.enums import AppointmentStatus, IngestionJobStatus, UserRole
from pgvector.sqlalchemy import Vector

"""
Container: Enum ek aisi class hai jo fixed values ko apne andar store karti hai aur hum is par loop chala sakte hain.
Data Validation (Gatekeeper): Yeh ek aisi strong guardrail/boundary hai ke tay shuda (pre-defined) values ke ilawa duniya ki koi aur value iske andar ghus hi nahi sakti. Agar koi koshish karega, toh system shuru mein hi error de kar rok dega.
"""
#helper function - accept only StrEnum, converts in the list of python-str
def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]


# 2 fields(colums) bnay gay hain
# ya class DB k andr record create or update ko track krny k lia use hoge
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column( #db k lia rules
        UTCDateTime(), # column ke type date+time honi chaiya
        nullable=False, # can't leave empty
        server_default=func.now() # bring current server side timee(not on the client side)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

# Base: database the parent class (which contains all the rules and propertiese that a DB needs)
# Base: batati hai ke kaunsi Python classes database ki tables banengi.
# Base: apny pass aik list maintain krta hai k kis kis na inherit kia hai( User, Appointment,) 
# Base.metadata.create_all(bind=engine) > SQLAlchemy base list chk krta hai, jino na inherit kia hota hai, un sab k SQL Tables db main jenerate kar daita hai
# 
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    """Database mein role naam ka ek column banao jo ek text/string ho (length 20 tak), ismein sirf wahi values aanay do jo UserRole class mein hain (values_callable aur create_constraint ki madad se validation lagao), aur isay khali mat chhorna (nullable=False)."""
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            values_callable=enum_values,
            length=20,
            create_constraint=True,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    patient_profile: Mapped[PatientProfile | None] = relationship(
        back_populates="user", uselist=False
    )
"""
back_populates="user"
Yeh dono tables ko aapas mein sync rakhta hai.
Iska matlab hai ke agar aap PatientProfile wali class mein ja kar dekhein ge, toh wahan bhi ek relation hoga jo user ko point kar raha hoga.
uselist=False > aik user ka aik patient profile"""



class PatientProfile(TimestampMixin, Base):
    __tablename__ = "patient_profiles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    phone_number: Mapped[str | None] = mapped_column(String(32))

    user: Mapped[User] = relationship(back_populates="patient_profile")
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="patient_profile"
    )


class Doctor(TimestampMixin, Base):
    __tablename__ = "doctors"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    availability_slots: Mapped[list[AvailabilitySlot]] = relationship(
        back_populates="doctor"
    )


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ends_after_starts"),
        UniqueConstraint(
            "doctor_id", "starts_at", "ends_at", name="uq_slot_doctor_interval"
        ),
        Index("ix_availability_slots_doctor_starts_at", "doctor_id", "starts_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    doctor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    doctor: Mapped[Doctor] = relationship(back_populates="availability_slots")
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="availability_slot"
    )


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index(
            "uq_appointments_active_slot",
            "availability_slot_id",
            unique=True,
            postgresql_where=text("status IN ('pending_approval', 'confirmed')"),
            sqlite_where=text("status IN ('pending_approval', 'confirmed')"),
        ),
        Index("ix_appointments_patient_status", "patient_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("patient_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    availability_slot_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("availability_slots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            name="appointment_status",
            native_enum=False,
            values_callable=enum_values,
            length=24,
            create_constraint=True,
        ),
        nullable=False,
    )
    is_flagged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    patient_profile: Mapped[PatientProfile] = relationship(
        back_populates="appointments"
    )
    availability_slot: Mapped[AvailabilitySlot] = relationship(
        back_populates="appointments"
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_target_created_at", "target_type", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.now()
    )


class IngestionJob(TimestampMixin, Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[IngestionJobStatus] = mapped_column(
        Enum(
            IngestionJobStatus,
            name="ingestion_job_status",
            native_enum=False,
            values_callable=enum_values,
            length=16,
            create_constraint=True,
        ),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(String(1000))


class FAQDocument(TimestampMixin, Base):
    __tablename__ = "faq_documents"
    __table_args__ = (
        Index(
            "ix_faq_documents_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_key: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict, server_default=text("'{}'")
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
