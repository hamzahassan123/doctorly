"""Add staff flag state to appointments.

Revision ID: 20261027_0002
Revises: 20261024_0001
Create Date: 2026-10-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261027_0002"
down_revision: Union[str, None] = "20261024_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column(
            "is_flagged",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("appointments", "is_flagged")
