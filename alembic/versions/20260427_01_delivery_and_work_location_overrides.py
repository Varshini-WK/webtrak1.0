"""add delivery and work location overrides

Revision ID: 20260427_01
Revises: 20260416_01
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260427_01"
down_revision = "20260416_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("delivery_status", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("work_location_type", sa.String(length=50), nullable=True))

    op.execute(
        """
        UPDATE users
        SET work_location_type = UPPER(work_mode)
        WHERE work_mode IS NOT NULL
          AND UPPER(work_mode) IN ('OFFSHORE', 'ONSITE', 'HYBRID', 'REMOTE')
        """
    )
    op.execute("UPDATE users SET delivery_status = 'NON_DELIVERABLE' WHERE delivery_status IS NULL")

    op.create_table(
        "allocation_work_location_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allocation_id", sa.Integer(), nullable=False),
        sa.Column("work_location_type", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allocation_id"),
    )


def downgrade() -> None:
    op.drop_table("allocation_work_location_overrides")
    op.drop_column("users", "work_location_type")
    op.drop_column("users", "delivery_status")
