"""Add embedded FAQ documents and the pgvector cosine index.

Revision ID: 20261027_0003
Revises: 20261027_0002
Create Date: 2026-10-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "20261027_0003"
down_revision: Union[str, None] = "20261027_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "faq_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_key", sa.String(length=150), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(384), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_faq_documents")),
        sa.UniqueConstraint(
            "document_key",
            name=op.f("uq_faq_documents_document_key"),
        ),
    )
    op.create_index(
        "ix_faq_documents_embedding_hnsw",
        "faq_documents",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_with={"m": 16, "ef_construction": 64},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_faq_documents_embedding_hnsw",
        table_name="faq_documents",
    )
    op.drop_table("faq_documents")
