"""drop attritions.updated_at and attritions.updated_by

Revision ID: 20260505_01
Revises: 20260504_01
Create Date: 2026-05-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260505_01"
down_revision = "20260504_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL drops the FK on updated_by when the column is dropped.
    op.drop_column("attritions", "updated_at")
    op.drop_column("attritions", "updated_by")


def downgrade() -> None:
    op.add_column(
        "attritions",
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.add_column("attritions", sa.Column("updated_by", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "attritions_updated_by_fkey",
        "attritions",
        "users",
        ["updated_by"],
        ["id"],
    )
