"""add timelogs table

Revision ID: 20260410_01
Revises:
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timelogs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("employee_email", sa.String(length=255), nullable=False),
        sa.Column("project_code", sa.String(length=100), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SUBMITTED"),
        sa.Column("manager_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_timelogs_user_id", "timelogs", ["user_id"])
    op.create_index("ix_timelogs_project_code", "timelogs", ["project_code"])
    op.create_index("ix_timelogs_employee_email", "timelogs", ["employee_email"])
    op.create_index("ix_timelogs_log_date", "timelogs", ["log_date"])
    op.create_index("ix_timelogs_status", "timelogs", ["status"])
    op.create_index("ix_timelogs_project_date_email", "timelogs", ["project_code", "log_date", "employee_email"])


def downgrade() -> None:
    op.drop_index("ix_timelogs_project_date_email", table_name="timelogs")
    op.drop_index("ix_timelogs_status", table_name="timelogs")
    op.drop_index("ix_timelogs_log_date", table_name="timelogs")
    op.drop_index("ix_timelogs_employee_email", table_name="timelogs")
    op.drop_index("ix_timelogs_project_code", table_name="timelogs")
    op.drop_index("ix_timelogs_user_id", table_name="timelogs")
    op.drop_table("timelogs")
