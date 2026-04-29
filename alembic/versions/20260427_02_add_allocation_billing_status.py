"""add billing status to allocations

Revision ID: 20260427_02
Revises: 20260427_01
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260427_02"
down_revision = "20260427_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("allocations", sa.Column("billing_status", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("allocations", "billing_status")
