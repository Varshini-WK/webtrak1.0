"""add allocation_roles table

Revision ID: 20260414_02
Revises: 20260414_01
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_02"
down_revision = "20260414_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allocation_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_allocation_roles_name"),
    )


def downgrade() -> None:
    op.drop_table("allocation_roles")
