"""attritions: resignation date and notice period days

Revision ID: 20260516_01
Revises: 20260514_01
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_01"
down_revision = "20260514_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attritions", sa.Column("resignation_date", sa.Date(), nullable=True))
    op.add_column("attritions", sa.Column("notice_period_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("attritions", "notice_period_days")
    op.drop_column("attritions", "resignation_date")
