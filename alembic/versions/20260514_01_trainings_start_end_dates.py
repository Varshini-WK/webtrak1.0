"""trainings: start_date and end_date replace duration_days

Revision ID: 20260514_01
Revises: 20260513_01
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_01"
down_revision = "20260513_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trainings", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("trainings", sa.Column("end_date", sa.Date(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE trainings
            SET
                start_date = (created_at AT TIME ZONE 'UTC')::date,
                end_date = (created_at AT TIME ZONE 'UTC')::date + (duration_days - 1)
            """
        )
    )
    op.alter_column("trainings", "start_date", existing_type=sa.Date(), nullable=False)
    op.alter_column("trainings", "end_date", existing_type=sa.Date(), nullable=False)
    op.drop_column("trainings", "duration_days")


def downgrade() -> None:
    op.add_column("trainings", sa.Column("duration_days", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE trainings
            SET duration_days = GREATEST(1, (end_date - start_date) + 1)
            """
        )
    )
    op.alter_column("trainings", "duration_days", existing_type=sa.Integer(), nullable=False)
    op.drop_column("trainings", "end_date")
    op.drop_column("trainings", "start_date")
