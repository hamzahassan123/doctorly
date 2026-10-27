"""Create the initial appointment and support domain schema.

Revision ID: 20261024_0001
Revises:
Create Date: 2026-10-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('patient', 'staff')", name=op.f("ck_users_user_role")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "doctors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("specialty", sa.String(length=120), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_doctors")),
    )
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name=op.f("ck_ingestion_jobs_ingestion_job_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_jobs")),
    )
    op.create_table(
        "patient_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_patient_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_patient_profiles")),
    )
    op.create_table(
        "availability_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "ends_at > starts_at", name=op.f("ck_availability_slots_ends_after_starts")
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name=op.f("fk_availability_slots_doctor_id_doctors"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_availability_slots")),
        sa.UniqueConstraint(
            "doctor_id", "starts_at", "ends_at", name="uq_slot_doctor_interval"
        ),
    )
    op.create_index(
        "ix_availability_slots_doctor_starts_at",
        "availability_slots",
        ["doctor_id", "starts_at"],
        unique=False,
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("availability_slot_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending_approval', 'confirmed', 'cancelled', 'completed')",
            name=op.f("ck_appointments_appointment_status"),
        ),
        sa.ForeignKeyConstraint(
            ["availability_slot_id"],
            ["availability_slots.id"],
            name=op.f("fk_appointments_availability_slot_id_availability_slots"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.user_id"],
            name=op.f("fk_appointments_patient_id_patient_profiles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointments")),
    )
    op.create_index(
        "ix_appointments_patient_status",
        "appointments",
        ["patient_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_appointments_active_slot",
        "appointments",
        ["availability_slot_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending_approval', 'confirmed')"),
        sqlite_where=sa.text("status IN ('pending_approval', 'confirmed')"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column(
            "details",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(
        "ix_audit_logs_target_created_at",
        "audit_logs",
        ["target_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_target_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("uq_appointments_active_slot", table_name="appointments")
    op.drop_index("ix_appointments_patient_status", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index(
        "ix_availability_slots_doctor_starts_at", table_name="availability_slots"
    )
    op.drop_table("availability_slots")
    op.drop_table("patient_profiles")
    op.drop_table("users")
    op.drop_table("ingestion_jobs")
    op.drop_table("doctors")
